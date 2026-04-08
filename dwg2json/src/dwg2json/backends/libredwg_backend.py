"""LibreDWG backend — converts DWG to DXF via LibreDWG, then parses with ezdxf.

Pipeline:
  1. ``dwg2dxf`` (LibreDWG CLI) converts the binary DWG to a text DXF
     in a temporary directory.
  2. ``ezdxf`` reads the DXF and exposes a rich Python object model.
  3. This module walks the ezdxf document to populate canonical models.

System dependency: LibreDWG must be installed and ``dwg2dxf`` must be
on ``$PATH`` (or set ``DWG2JSON_DWG2DXF`` to the full path of the binary).
``ezdxf`` is a pip dependency.
"""

from __future__ import annotations

import logging
import math
import os
import shutil
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from ..models import (
    BlockDefinition,
    DwgJsonDocument,
    Entity,
    Layer,
    Layout,
    ParseOptions,
    ParseResult,
    ParserInfo,
    Point3D,
    SourceDocument,
    ViewportRecord,
    WarningRecord,
    XrefGraphNode,
)
from .base import DwgBackend

log = logging.getLogger(__name__)


def _format_subprocess_failure(tool: str, exc: subprocess.CalledProcessError) -> str:
    """Build a concise error string including stderr/stdout when present."""
    msg = f"{tool} failed with exit code {exc.returncode}"
    err_out = (exc.stderr or "").strip() or (exc.stdout or "").strip()
    if not err_out:
        return msg
    if len(err_out) > 800:
        err_out = err_out[:800] + "…"
    return f"{msg}: {err_out}"


# Entity types we know how to map.  Anything else gets a best-effort
# generic mapping with a warning.
_KNOWN_TYPES: set[str] = {
    "LINE", "CIRCLE", "ARC", "ELLIPSE", "POINT",
    "LWPOLYLINE", "POLYLINE", "SPLINE",
    "TEXT", "MTEXT", "ATTRIB", "ATTDEF",
    "INSERT",
    "DIMENSION", "ALIGNED_DIMENSION", "ROTATED_DIMENSION",
    "ANGULAR_DIMENSION", "ANGULAR_3P_DIMENSION",
    "ORDINATE_DIMENSION", "DIAMETRIC_DIMENSION", "RADIAL_DIMENSION",
    "ARC_DIMENSION",
    "LEADER", "MULTILEADER", "MLEADER",
    "HATCH", "MPOLYGON",
    "IMAGE", "WIPEOUT",
    "SOLID", "3DSOLID", "3DFACE", "MESH", "BODY", "REGION", "SURFACE",
    "RAY", "XLINE",
    "VIEWPORT",
    "TABLE",
    "MLINE",
    "TRACE",
    "SHAPE",
    "HELIX",
    "UNDERLAY", "PDFUNDERLAY", "DGNUNDERLAY", "DWFUNDERLAY",
}


class LibreDwgBackend(DwgBackend):
    name = "libredwg"
    version: str | None = None

    def __init__(self) -> None:
        self._dwg2dxf = None
        env_bin = os.environ.get("DWG2JSON_DWG2DXF", "").strip()
        if env_bin:
            p = Path(env_bin)
            if p.is_file():
                self._dwg2dxf = str(p)
        if self._dwg2dxf is None:
            self._dwg2dxf = shutil.which("dwg2dxf")
        if self._dwg2dxf:
            self._detect_version()

    def is_available(self) -> bool:
        return self._dwg2dxf is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, path: Path, options: ParseOptions) -> ParseResult:
        root_id = self._source_id(path)
        exists = path.exists()

        if not exists:
            return self._failed_result(root_id, path, "Source file does not exist.")

        try:
            import ezdxf
        except ImportError:
            return self._failed_result(
                root_id, path,
                "ezdxf is not installed. Install with: pip install dwg2json[libredwg]",
            )

        if path.suffix.lower() == ".dxf":
            try:
                dxf_doc = ezdxf.readfile(str(path))
            except Exception as exc:
                return self._failed_result(root_id, path, f"ezdxf failed to read DXF: {exc}")
            return self._build_result(root_id, path, dxf_doc, options)

        if not self._dwg2dxf:
            return self._fallback_result(root_id, path)

        try:
            with tempfile.TemporaryDirectory(prefix="dwg2json_") as tmp:
                dxf_path = Path(tmp) / f"{path.stem}.dxf"
                self._run_dwg2dxf(path, dxf_path)
                dxf_doc = ezdxf.readfile(str(dxf_path))
        except subprocess.CalledProcessError as exc:
            detail = _format_subprocess_failure("dwg2dxf", exc)
            return self._failed_result(root_id, path, detail)
        except OSError as exc:
            return self._failed_result(root_id, path, f"dwg2dxf conversion failed: {exc}")
        except Exception as exc:
            return self._failed_result(root_id, path, f"ezdxf failed to read DXF: {exc}")

        return self._build_result(root_id, path, dxf_doc, options)

    # ------------------------------------------------------------------
    # DWG → DXF conversion
    # ------------------------------------------------------------------

    def _run_dwg2dxf(self, dwg_path: Path, out_dxf: Path) -> None:
        assert self._dwg2dxf is not None
        subprocess.run(
            [self._dwg2dxf, "-y", "-o", str(out_dxf), str(dwg_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if not out_dxf.exists():
            raise FileNotFoundError(f"dwg2dxf did not produce {out_dxf}")

    # ------------------------------------------------------------------
    # Build result from ezdxf document
    # ------------------------------------------------------------------

    def _build_result(
        self,
        root_id: str,
        path: Path,
        dxf_doc: Any,
        options: ParseOptions,
    ) -> ParseResult:
        warnings: list[WarningRecord] = []
        layers = self._extract_layers(root_id, dxf_doc, options)
        layouts = self._extract_layouts(root_id, dxf_doc)
        blocks, raw_xrefs = self._extract_blocks(root_id, dxf_doc)
        layers_by_name = {la.name: la for la in layers}
        vp_by_layout: dict[str, list[ViewportRecord]] = defaultdict(list)
        entities, entity_warnings = self._extract_entities(
            root_id, dxf_doc, options, layers_by_name, vp_by_layout
        )
        warnings.extend(entity_warnings)
        self._merge_viewports_into_layouts(layouts, vp_by_layout, options)
        doc_metadata = self._extract_metadata(dxf_doc)
        doc_metadata["raw_xrefs"] = raw_xrefs

        source = SourceDocument(
            id=root_id,
            path=str(path),
            resolved_path=str(path.resolve()),
            role="root",
            exists=True,
            parsed=True,
            parse_status="parsed",
            metadata=doc_metadata,
            layers=layers,
            layouts=layouts,
            blocks=blocks,
            entities=entities,
            warnings=warnings,
        )

        document = DwgJsonDocument(
            parser=ParserInfo(
                backend=self.name,
                backend_version=self.version,
            ),
            root_source_id=root_id,
            sources=[source],
            warnings=list(warnings),
        )
        document.xref_graph.nodes.append(
            XrefGraphNode(
                source_id=root_id,
                path=str(path),
                resolved_path=str(path.resolve()),
                exists=True,
                parsed=True,
                parse_status="parsed",
                depth=0,
            )
        )
        return ParseResult(document=document)

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _extract_metadata(self, dxf_doc: Any) -> dict[str, Any]:
        meta: dict[str, Any] = {"backend": self.name}
        try:
            header = dxf_doc.header
            meta["dwg_version"] = str(getattr(header, "version", None))
            units_var = header.get("$INSUNITS", None)
            if units_var is not None:
                meta["units"] = _UNIT_MAP.get(int(units_var), f"code_{units_var}")
            for var_name in ("$EXTMIN", "$EXTMAX"):
                val = header.get(var_name, None)
                if val is not None:
                    meta[var_name.lstrip("$").lower()] = list(val)
        except Exception:
            pass
        try:
            summary = dxf_doc.ezdxf_metadata()
            if summary:
                meta["ezdxf_metadata"] = str(summary)
        except Exception:
            pass
        return meta

    def _extract_layers(self, root_id: str, dxf_doc: Any, options: ParseOptions) -> list[Layer]:
        layers: list[Layer] = []
        try:
            for la in dxf_doc.layers:
                color = la.dxf.get("color", None)
                kwargs: dict[str, Any] = {
                    "id": f"{root_id}__layer_{la.dxf.name}",
                    "name": la.dxf.name,
                    "color_index": int(color) if color is not None else None,
                    "line_type": la.dxf.get("linetype", None),
                    "is_frozen": la.is_frozen(),
                    "is_locked": la.is_locked(),
                    "is_off": la.is_off(),
                }
                if options.emit_layer_plot_flags:
                    try:
                        raw_plot = la.dxf.get("plot", None)
                        if raw_plot is not None:
                            kwargs["is_plottable"] = bool(raw_plot)
                        else:
                            kwargs["is_plottable"] = True
                    except Exception:
                        pass
                layers.append(Layer(**kwargs))
        except Exception as exc:
            log.warning("Layer extraction error: %s", exc)
        return layers

    def _extract_layouts(self, root_id: str, dxf_doc: Any) -> list[Layout]:
        layouts: list[Layout] = []
        try:
            for idx, layout in enumerate(dxf_doc.layouts):
                layouts.append(
                    Layout(
                        id=f"{root_id}__layout_{layout.name}",
                        name=layout.name,
                        is_model_space=(layout.name == "Model"),
                        tab_order=idx,
                    )
                )
        except Exception as exc:
            log.warning("Layout extraction error: %s", exc)
        return layouts

    def _extract_blocks(
        self, root_id: str, dxf_doc: Any
    ) -> tuple[list[BlockDefinition], list[dict]]:
        blocks: list[BlockDefinition] = []
        raw_xrefs: list[dict] = []
        try:
            for blk in dxf_doc.blocks:
                is_xref = getattr(blk, "is_xref", False)
                xref_path = blk.dxf.get("xref_path", None) if is_xref else None
                origin_raw = blk.dxf.get("base_point", None)
                origin = (
                    Point3D(x=origin_raw[0], y=origin_raw[1], z=origin_raw[2])
                    if origin_raw is not None
                    else None
                )
                block_def = BlockDefinition(
                    id=f"{root_id}__block_{blk.name}",
                    name=blk.name,
                    is_xref=is_xref,
                    xref_path=str(xref_path) if xref_path else None,
                    origin=origin,
                    is_anonymous=blk.name.startswith("*"),
                )
                blocks.append(block_def)

                if is_xref and xref_path:
                    mode = "overlay" if _is_overlay(blk) else "attach"
                    raw_xrefs.append({
                        "path": str(xref_path),
                        "mode": mode,
                        "block_name": blk.name,
                        "transform": None,
                    })
        except Exception as exc:
            log.warning("Block extraction error: %s", exc)
        return blocks, raw_xrefs

    def _extract_entities(
        self,
        root_id: str,
        dxf_doc: Any,
        options: ParseOptions,
        layers_by_name: dict[str, Layer],
        vp_by_layout: dict[str, list[ViewportRecord]],
    ) -> tuple[list[Entity], list[WarningRecord]]:
        entities: list[Entity] = []
        warnings: list[WarningRecord] = []
        unsupported: set[str] = set()

        for layout in dxf_doc.layouts:
            layout_name = layout.name
            for dxf_entity in layout:
                try:
                    ent = self._map_entity(
                        root_id,
                        dxf_entity,
                        layout_name,
                        options,
                        layers_by_name,
                        vp_by_layout,
                    )
                    if ent is not None:
                        entities.append(ent)
                        etype = dxf_entity.dxftype()
                        if etype not in _KNOWN_TYPES and etype not in unsupported:
                            unsupported.add(etype)
                except Exception as exc:
                    handle = str(getattr(dxf_entity.dxf, "handle", "?"))
                    warnings.append(
                        WarningRecord(
                            code="entity-extraction-error",
                            message=f"Error extracting entity {handle}: {exc}",
                            severity="warning",
                            source_id=root_id,
                            handle=handle,
                        )
                    )

        for etype in sorted(unsupported):
            warnings.append(
                WarningRecord(
                    code="unsupported-entity-type",
                    message=f"Unsupported entity type: {etype}",
                    severity="info",
                    source_id=root_id,
                )
            )
        return entities, warnings

    def _map_entity(
        self,
        root_id: str,
        dxf_entity: Any,
        layout_name: str,
        options: ParseOptions,
        layers_by_name: dict[str, Layer],
        vp_by_layout: dict[str, list[ViewportRecord]],
    ) -> Entity | None:
        dxf = dxf_entity.dxf
        handle = str(dxf.get("handle", ""))
        owner = str(dxf.get("owner", "")) if dxf.get("owner", None) else None
        etype = dxf_entity.dxftype()
        layer = dxf.get("layer", None)

        ent = Entity(
            id=f"{root_id}__ent_{handle}",
            source_id=root_id,
            handle=handle,
            owner_handle=owner,
            type=etype,
            layer=layer,
            layout=layout_name,
            color_index=dxf.get("color", None),
            line_type=dxf.get("linetype", None),
        )

        ent.space_class = "model" if layout_name == "Model" else "paper"
        if options.emit_layer_plot_flags and layer:
            lao = layers_by_name.get(str(layer))
            if lao is not None and lao.is_plottable is not None:
                ent.non_plot_candidate = not lao.is_plottable

        if options.emit_viewport_records and etype == "VIEWPORT":
            vp_rec = _build_viewport_record(root_id, layout_name, dxf_entity, options)
            if vp_rec is not None:
                vp_by_layout[layout_name].append(vp_rec)

        # Text content
        if etype in ("TEXT", "MTEXT", "ATTRIB", "ATTDEF"):
            ent.text = _safe_text(dxf_entity)

        # INSERT / block reference
        if etype == "INSERT":
            ent.block_name = dxf.get("name", None)
            ins = dxf.get("insert", None)
            if ins is not None:
                if hasattr(ins, "get"):
                    ins_z = ins.get(2, 0.0)
                else:
                    ins_z = ins[2] if len(ins) > 2 else 0.0
                ent.insert_point = Point3D(x=ins[0], y=ins[1], z=ins_z)
            xs = dxf.get("xscale", 1.0)
            ys = dxf.get("yscale", 1.0)
            zs = dxf.get("zscale", 1.0)
            ent.scale = Point3D(x=xs, y=ys, z=zs)
            ent.rotation = dxf.get("rotation", 0.0)

            # Attributes on inserts
            if hasattr(dxf_entity, "attribs"):
                for attrib in dxf_entity.attribs:
                    tag = attrib.dxf.get("tag", "")
                    val = attrib.dxf.get("text", "")
                    if tag:
                        ent.attributes[tag] = val

        # Geometry payload (type-specific)
        ent.geometry = _extract_geometry(dxf_entity, etype)

        # Dimension text
        if "DIMENSION" in etype:
            ent.text = _safe_text(dxf_entity)

        # Raw payload
        if options.keep_raw_payloads:
            ent.raw = _safe_raw(dxf_entity)

        return ent

    # ------------------------------------------------------------------
    # Fallback / failure helpers
    # ------------------------------------------------------------------

    def _fallback_result(self, root_id: str, path: Path) -> ParseResult:
        """Return a stub result when LibreDWG is not installed."""
        source = SourceDocument(
            id=root_id,
            path=str(path),
            resolved_path=str(path.resolve()) if path.exists() else None,
            role="root",
            exists=path.exists(),
            parsed=False,
            parse_status="partial",
            metadata={"raw_xrefs": [], "backend": "libredwg", "note": "dwg2dxf not found on PATH"},
            warnings=[
                WarningRecord(
                    code="backend-unavailable",
                    message=(
                        "LibreDWG (dwg2dxf) is not installed or not on PATH. "
                        "Install LibreDWG to enable DWG decoding."
                    ),
                    severity="error",
                    source_id=root_id,
                ),
            ],
        )
        document = DwgJsonDocument(
            parser=ParserInfo(backend=self.name, backend_version=self.version),
            root_source_id=root_id,
            sources=[source],
            warnings=list(source.warnings),
        )
        document.xref_graph.nodes.append(
            XrefGraphNode(
                source_id=root_id,
                path=str(path),
                resolved_path=str(path.resolve()) if path.exists() else None,
                exists=path.exists(),
                parsed=False,
                parse_status="partial",
                depth=0,
            )
        )
        return ParseResult(document=document)

    def _failed_result(self, root_id: str, path: Path, reason: str) -> ParseResult:
        source = SourceDocument(
            id=root_id,
            path=str(path),
            resolved_path=str(path.resolve()) if path.exists() else None,
            role="root",
            exists=path.exists(),
            parsed=False,
            parse_status="failed",
            metadata={"raw_xrefs": [], "backend": self.name, "failure_reason": reason},
            warnings=[
                WarningRecord(
                    code="parse-failed",
                    message=reason,
                    severity="error",
                    source_id=root_id,
                ),
            ],
        )
        document = DwgJsonDocument(
            parser=ParserInfo(backend=self.name, backend_version=self.version),
            root_source_id=root_id,
            sources=[source],
            warnings=list(source.warnings),
        )
        document.xref_graph.nodes.append(
            XrefGraphNode(
                source_id=root_id,
                path=str(path),
                exists=path.exists(),
                parsed=False,
                parse_status="failed",
                depth=0,
            )
        )
        return ParseResult(document=document)

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------

    def _detect_version(self) -> None:
        assert self._dwg2dxf is not None
        try:
            result = subprocess.run(
                [self._dwg2dxf, "--version"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            out = result.stdout.strip() or result.stderr.strip()
            if out:
                self.version = out.split("\n")[0].strip()
        except Exception:
            pass

    @staticmethod
    def _source_id(path: Path) -> str:
        stem = path.stem.replace(" ", "_") or "drawing"
        return f"src-{stem.lower()}"

    @staticmethod
    def _merge_viewports_into_layouts(
        layouts: list[Layout],
        vp_by_layout: dict[str, list[ViewportRecord]],
        options: ParseOptions,
    ) -> None:
        if not options.emit_viewport_records:
            return
        by_name = {ly.name: ly for ly in layouts}
        for name, vps in vp_by_layout.items():
            ly = by_name.get(name)
            if ly is None:
                continue
            ly.viewports = sorted(vps, key=lambda v: v.handle)


# ======================================================================
# Module-level helper functions
# ======================================================================

_UNIT_MAP: dict[int, str] = {
    0: "unitless", 1: "inches", 2: "feet", 3: "miles", 4: "millimeters",
    5: "centimeters", 6: "meters", 7: "kilometers", 8: "microinches",
    9: "mils", 10: "yards", 11: "angstroms", 12: "nanometers",
    13: "microns", 14: "decimeters", 15: "decameters", 16: "hectometers",
    17: "gigameters", 18: "astronomical_units", 19: "light_years",
    20: "parsecs",
}


def _is_overlay(blk: Any) -> bool:
    """Best-effort detection of overlay vs attach mode."""
    try:
        flags = blk.dxf.get("flags", 0)
        return bool(flags & 8)
    except Exception:
        return False


def _clean_handle(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s == "0":
        return None
    return s


def _build_viewport_record(
    root_id: str,
    layout_name: str,
    dxf_entity: Any,
    options: ParseOptions,
) -> ViewportRecord | None:
    dxf = dxf_entity.dxf
    handle = str(dxf.get("handle", ""))
    if not handle:
        return None

    center = _vec(dxf.get("center", None))
    width = dxf.get("width", None)
    height = dxf.get("height", None)
    vcp = dxf.get("view_center_point", None)
    view_center_model: list[float] | None = None
    if vcp is not None:
        try:
            view_center_model = [float(vcp[0]), float(vcp[1]), 0.0]
        except Exception:
            view_center_model = None
    view_height_model = dxf.get("view_height", None)
    scale_zoom_xp: float | None = None
    try:
        if width is not None and view_height_model is not None:
            vh = float(view_height_model)
            if vh != 0.0:
                scale_zoom_xp = float(width) / vh
    except (TypeError, ValueError):
        pass

    frozen: list[str] = []
    if options.emit_vp_layer_overrides:
        try:
            frozen = sorted(str(n) for n in dxf_entity.frozen_layers)
        except Exception:
            frozen = []

    vp_id = dxf.get("id", None)
    meta: dict[str, Any] = {}
    try:
        if vp_id is not None and int(vp_id) == 1:
            meta["is_layout_tab_viewport"] = True
    except (TypeError, ValueError):
        pass

    return ViewportRecord(
        id=f"{root_id}__vp_{handle}",
        handle=handle,
        owner_layout=layout_name,
        viewport_dxf_id=int(vp_id) if vp_id is not None else None,
        status=dxf.get("status", None),
        paper_center=center,
        paper_width=float(width) if width is not None else None,
        paper_height=float(height) if height is not None else None,
        view_center_model=view_center_model,
        view_height_model=float(view_height_model) if view_height_model is not None else None,
        scale_zoom_xp=scale_zoom_xp,
        view_direction=_vec(dxf.get("view_direction_vector", None)),
        view_target=_vec(dxf.get("view_target_point", None)),
        view_twist_angle=dxf.get("view_twist_angle", None),
        ucs_ortho_type=dxf.get("ucs_ortho_type", None),
        ucs_handle=_clean_handle(dxf.get("ucs_handle", None)),
        clipping_boundary_handle=_clean_handle(dxf.get("clipping_boundary_handle", None)),
        frozen_layer_names=frozen,
        flags=dxf.get("flags", None),
        plot_style_name=(str(dxf.get("plot_style_name", "") or None) or None),
        render_mode=dxf.get("render_mode", None),
        metadata=meta,
    )


def _safe_text(entity: Any) -> str | None:
    for attr in ("text", "plain_text"):
        try:
            fn = getattr(entity, attr, None)
            if callable(fn):
                return fn()
            val = getattr(entity.dxf, attr, None)
            if val is not None:
                return str(val)
        except Exception:
            continue
    try:
        return str(entity.dxf.get("text", None))
    except Exception:
        return None


def _extract_geometry(entity: Any, etype: str) -> dict[str, Any]:
    """Build a type-specific geometry payload dict."""
    g: dict[str, Any] = {}
    dxf = entity.dxf
    try:
        match etype:
            case "LINE":
                g["start"] = _vec(dxf.get("start", None))
                g["end"] = _vec(dxf.get("end", None))
            case "CIRCLE":
                g["center"] = _vec(dxf.get("center", None))
                g["radius"] = dxf.get("radius", None)
            case "ARC":
                g["center"] = _vec(dxf.get("center", None))
                g["radius"] = dxf.get("radius", None)
                g["start_angle"] = dxf.get("start_angle", None)
                g["end_angle"] = dxf.get("end_angle", None)
            case "ELLIPSE":
                g["center"] = _vec(dxf.get("center", None))
                g["major_axis"] = _vec(dxf.get("major_axis", None))
                g["ratio"] = dxf.get("ratio", None)
                g["start_param"] = dxf.get("start_param", None)
                g["end_param"] = dxf.get("end_param", None)
            case "LWPOLYLINE":
                try:
                    g["vertices"] = [list(pt) for pt in entity.get_points(format="xyseb")]
                    g["is_closed"] = entity.closed
                except Exception:
                    pass
            case "SPLINE":
                try:
                    g["degree"] = entity.dxf.get("degree", None)
                    g["control_points"] = [list(pt) for pt in entity.control_points]
                    g["knots"] = list(entity.knots)
                    g["is_closed"] = entity.closed
                except Exception:
                    pass
            case "POINT":
                g["location"] = _vec(dxf.get("location", None))
            case "HATCH" | "MPOLYGON":
                try:
                    g["pattern_name"] = entity.dxf.get("pattern_name", None)
                    g["solid_fill"] = entity.dxf.get("solid_fill", None)
                    g["boundary_path_count"] = len(entity.paths)
                except Exception:
                    pass
            case "INSERT":
                g["insert"] = _vec(dxf.get("insert", None))
                g["block_name"] = dxf.get("name", None)
                xs = dxf.get("xscale", 1.0)
                ys = dxf.get("yscale", 1.0)
                zs = dxf.get("zscale", 1.0)
                rot = dxf.get("rotation", 0.0)
                g["scale"] = [xs, ys, zs]
                g["rotation"] = rot
                g["transform_4x4"] = _insert_transform(
                    dxf.get("insert", (0, 0, 0)), xs, ys, zs, rot
                )
            case s if "DIMENSION" in s:
                g["defpoint"] = _vec(dxf.get("defpoint", None))
                g["text_midpoint"] = _vec(dxf.get("text_midpoint", None))
                g["measurement"] = getattr(entity, "measurement", None)
            case "LEADER" | "MULTILEADER" | "MLEADER":
                try:
                    if hasattr(entity, "vertices"):
                        g["vertices"] = [list(v) for v in entity.vertices]
                except Exception:
                    pass
            case "3DFACE" | "SOLID" | "TRACE":
                for i in range(4):
                    key = f"vtx{i}"
                    val = dxf.get(key, None)
                    if val is not None:
                        g[key] = _vec(val)
            case "IMAGE" | "WIPEOUT":
                g["insert_point"] = _vec(dxf.get("insert", None))
                g["image_size"] = _vec(dxf.get("image_size", None))
            case "VIEWPORT":
                g["center"] = _vec(dxf.get("center", None))
                g["width"] = dxf.get("width", None)
                g["height"] = dxf.get("height", None)
                g["status"] = dxf.get("status", None)
                g["viewport_id"] = dxf.get("id", None)
                g["view_center_point"] = _vec2_to_3(dxf.get("view_center_point", None))
                g["view_height"] = dxf.get("view_height", None)
                g["view_direction_vector"] = _vec(dxf.get("view_direction_vector", None))
                g["view_target_point"] = _vec(dxf.get("view_target_point", None))
                g["clipping_boundary_handle"] = _clean_handle(
                    dxf.get("clipping_boundary_handle", None)
                )
    except Exception:
        pass
    return {k: v for k, v in g.items() if v is not None}


def _vec2_to_3(val: Any) -> list[float] | None:
    if val is None:
        return None
    try:
        return [float(val[0]), float(val[1]), 0.0]
    except (TypeError, ValueError, IndexError):
        return None


def _vec(val: Any) -> list[float] | None:
    if val is None:
        return None
    try:
        return [float(v) for v in val]
    except (TypeError, ValueError):
        return None


def _insert_transform(
    insert: Any, xs: float, ys: float, zs: float, rotation_deg: float
) -> list[list[float]]:
    """Build a 4×4 homogeneous transform for an INSERT placement."""
    r = math.radians(rotation_deg)
    c, s = math.cos(r), math.sin(r)
    try:
        tx = float(insert[0])
        ty = float(insert[1])
        tz = float(insert[2]) if len(insert) > 2 else 0.0
    except Exception:
        tx = ty = tz = 0.0
    return [
        [xs * c, -ys * s, 0.0, tx],
        [xs * s,  ys * c, 0.0, ty],
        [0.0,     0.0,    zs,  tz],
        [0.0,     0.0,    0.0, 1.0],
    ]


def _safe_raw(entity: Any) -> dict[str, Any]:
    """Extract a small subset of raw DXF data for provenance."""
    raw: dict[str, Any] = {}
    try:
        dxf = entity.dxf
        for attr in ("handle", "owner", "layer", "color", "linetype", "lineweight"):
            val = dxf.get(attr, None)
            if val is not None:
                raw[attr] = str(val) if not isinstance(val, int | float) else val
    except Exception:
        pass
    return raw
