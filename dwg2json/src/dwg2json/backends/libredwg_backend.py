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
    WarningRecord,
    XrefGraphNode,
)
from .base import DwgBackend

log = logging.getLogger(__name__)

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

        if not self._dwg2dxf:
            return self._fallback_result(root_id, path)

        try:
            dxf_path = self._convert_to_dxf(path)
        except (subprocess.CalledProcessError, OSError) as exc:
            return self._failed_result(root_id, path, f"dwg2dxf conversion failed: {exc}")

        try:
            import ezdxf
        except ImportError:
            return self._failed_result(
                root_id, path,
                "ezdxf is not installed. Install with: pip install dwg2json[libredwg]",
            )

        try:
            dxf_doc = ezdxf.readfile(str(dxf_path))
        except Exception as exc:
            return self._failed_result(root_id, path, f"ezdxf failed to read DXF: {exc}")

        return self._build_result(root_id, path, dxf_doc, options)

    # ------------------------------------------------------------------
    # DWG → DXF conversion
    # ------------------------------------------------------------------

    def _convert_to_dxf(self, dwg_path: Path) -> Path:
        assert self._dwg2dxf is not None
        tmp_dir = Path(tempfile.mkdtemp(prefix="dwg2json_"))
        out_path = tmp_dir / f"{dwg_path.stem}.dxf"
        subprocess.run(
            [self._dwg2dxf, "-y", "-o", str(out_path), str(dwg_path)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        if not out_path.exists():
            raise FileNotFoundError(f"dwg2dxf did not produce {out_path}")
        return out_path

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
        layers = self._extract_layers(root_id, dxf_doc)
        layouts = self._extract_layouts(root_id, dxf_doc)
        blocks, raw_xrefs = self._extract_blocks(root_id, dxf_doc)
        entities, entity_warnings = self._extract_entities(root_id, dxf_doc, options)
        warnings.extend(entity_warnings)
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

    def _extract_layers(self, root_id: str, dxf_doc: Any) -> list[Layer]:
        layers: list[Layer] = []
        try:
            for la in dxf_doc.layers:
                color = la.dxf.get("color", None)
                layers.append(
                    Layer(
                        id=f"{root_id}__layer_{la.dxf.name}",
                        name=la.dxf.name,
                        color_index=int(color) if color is not None else None,
                        line_type=la.dxf.get("linetype", None),
                        is_frozen=la.is_frozen(),
                        is_locked=la.is_locked(),
                        is_off=la.is_off(),
                    )
                )
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
                is_xref = blk.is_xref
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
    ) -> tuple[list[Entity], list[WarningRecord]]:
        entities: list[Entity] = []
        warnings: list[WarningRecord] = []
        unsupported: set[str] = set()

        for layout in dxf_doc.layouts:
            layout_name = layout.name
            for dxf_entity in layout:
                try:
                    ent = self._map_entity(root_id, dxf_entity, layout_name, options)
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
                timeout=5,
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
    except Exception:
        pass
    return {k: v for k, v in g.items() if v is not None}


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
