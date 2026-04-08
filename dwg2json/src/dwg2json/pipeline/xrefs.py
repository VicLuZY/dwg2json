"""Recursive xref resolver with cache, cycle guard, and missing-reference recording."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from ..models import (
    MissingReference,
    ParseOptions,
    ParseResult,
    SourceDocument,
    WarningRecord,
    XrefBindingMetadata,
    XrefGraphEdge,
    XrefGraphNode,
    XrefMode,
)
from .xref_paths import normalize_xref_path, resolve_candidate_paths


class XrefResolver:
    def __init__(self, backend) -> None:  # noqa: ANN001 – avoids circular import
        self.backend = backend
        self._cache: dict[str, ParseResult] = {}

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def resolve(self, result: ParseResult, options: ParseOptions) -> ParseResult:
        root_source = result.document.root_source
        root_path = Path(root_source.path)
        visited: set[str] = set()
        if root_path.exists():
            visited.add(str(root_path.resolve()))
        else:
            visited.add(str(root_path))

        self._resolve_for_source(
            result=result,
            host_source=root_source,
            host_path=root_path,
            depth=0,
            visited=visited,
            options=options,
        )
        return result

    # ------------------------------------------------------------------
    # Recursive resolver
    # ------------------------------------------------------------------

    def _resolve_for_source(
        self,
        result: ParseResult,
        host_source: SourceDocument,
        host_path: Path,
        depth: int,
        visited: set[str],
        options: ParseOptions,
    ) -> None:
        if depth >= options.max_xref_depth:
            result.document.warnings.append(
                WarningRecord(
                    code="xref-depth-limit",
                    message=(
                        f"Max xref depth ({options.max_xref_depth}) reached "
                        f"while resolving children of {host_source.id}."
                    ),
                    severity="warning",
                    source_id=host_source.id,
                )
            )
            return

        raw_xrefs: list[dict] = host_source.metadata.get("raw_xrefs", [])
        for index, raw in enumerate(raw_xrefs):
            raw_path: str | None = raw.get("path")
            mode = cast(XrefMode, raw.get("mode", "unknown"))
            transform = raw.get("transform")
            insertion_point = raw.get("insertion_point")
            child_id = self._child_id(host_source.id, index, raw_path)
            candidates = resolve_candidate_paths(
                host_path.parent, raw_path, options.xref_search_roots
            )
            resolved = next((c for c in candidates if c.exists()), None)

            if resolved is None:
                self._record_missing(
                    result, host_source, child_id, raw_path, mode, transform,
                    insertion_point, candidates, depth, options,
                )
                continue

            key = str(resolved.resolve())
            if key in visited:
                self._record_cycle(
                    result, host_source, child_id, raw_path, key,
                    mode, transform, insertion_point, resolved, depth,
                )
                continue

            visited.add(key)
            self._record_resolved(
                result, host_source, child_id, raw_path, mode, transform,
                insertion_point, candidates, resolved, depth, options, visited,
            )

    # ------------------------------------------------------------------
    # Missing xref
    # ------------------------------------------------------------------

    def _record_missing(
        self,
        result: ParseResult,
        host_source: SourceDocument,
        child_id: str,
        raw_path: str | None,
        mode: XrefMode,
        transform: list | None,
        insertion_point: dict | None,
        candidates: list[Path],
        depth: int,
        options: ParseOptions,
    ) -> None:
        if options.missing_xref_policy == "error":
            raise FileNotFoundError(
                f"Missing xref dependency: {raw_path} "
                f"(host={host_source.id}, candidates={[str(c) for c in candidates]})"
            )

        child_source = SourceDocument(
            id=child_id,
            path=raw_path or "",
            resolved_path=None,
            role="xref",
            exists=False,
            parsed=False,
            parse_status="missing",
            parent_source_id=host_source.id,
            xref_binding=XrefBindingMetadata(
                saved_path=raw_path,
                resolved_path=None,
                mode=mode,
                transform=transform,
                exists=False,
                parsed=False,
                missing_reason="Xref target not found on any candidate path.",
                candidate_paths=[str(p) for p in candidates],
            ),
            warnings=[
                WarningRecord(
                    code="xref-missing",
                    message=f"Missing xref dependency: {raw_path}",
                    severity="warning",
                    source_id=child_id,
                )
            ],
        )
        result.document.sources.append(child_source)
        result.document.xref_graph.nodes.append(
            XrefGraphNode(
                source_id=child_id,
                path=raw_path or "",
                resolved_path=None,
                exists=False,
                parsed=False,
                parse_status="missing",
                parent_source_id=host_source.id,
                depth=depth + 1,
            )
        )
        result.document.xref_graph.edges.append(
            XrefGraphEdge(
                host_source_id=host_source.id,
                target_source_id=child_id,
                saved_path=raw_path,
                resolved_path=None,
                mode=mode,
                transform=transform,
                exists=False,
                parsed=False,
                composition_required=True,
            )
        )
        result.document.missing_references.append(
            MissingReference(
                kind="xref",
                requested_path=raw_path,
                normalized_path=normalize_xref_path(raw_path) if raw_path else None,
                resolver_root=str(Path(host_source.path).parent),
                parent_document_id=host_source.id,
                host_handles=[],
                impact_summary=(
                    "Missing xref prevented full composite interpretation of "
                    "overlay geometry."
                ),
                severity="high",
                interpretation_impacted=True,
            )
        )
        result.document.warnings.append(
            WarningRecord(
                code="xref-missing",
                message=(
                    f"Missing xref dependency prevents full composition: {raw_path}. "
                    "Referenced background drawing was unavailable. "
                    "Spatial relationships may be incomplete."
                ),
                severity="warning",
                source_id=host_source.id,
            )
        )

    # ------------------------------------------------------------------
    # Cycle-blocked xref
    # ------------------------------------------------------------------

    def _record_cycle(
        self,
        result: ParseResult,
        host_source: SourceDocument,
        child_id: str,
        raw_path: str | None,
        resolved_key: str,
        mode: XrefMode,
        transform: list | None,
        insertion_point: dict | None,
        resolved: Path,
        depth: int,
    ) -> None:
        child_source = SourceDocument(
            id=child_id,
            path=raw_path or str(resolved),
            resolved_path=resolved_key,
            role="xref",
            exists=True,
            parsed=False,
            parse_status="unresolved",
            parent_source_id=host_source.id,
            xref_binding=XrefBindingMetadata(
                saved_path=raw_path,
                resolved_path=resolved_key,
                mode=mode,
                transform=transform,
                exists=True,
                parsed=False,
                missing_reason="Recursive xref loop detected. Reference expansion stopped safely.",
            ),
            warnings=[
                WarningRecord(
                    code="xref-cycle",
                    message=f"Cycle detected for {resolved}: already visited.",
                    severity="warning",
                    source_id=child_id,
                )
            ],
        )
        result.document.sources.append(child_source)
        result.document.xref_graph.nodes.append(
            XrefGraphNode(
                source_id=child_id,
                path=raw_path or str(resolved),
                resolved_path=resolved_key,
                exists=True,
                parsed=False,
                parse_status="unresolved",
                parent_source_id=host_source.id,
                depth=depth + 1,
            )
        )
        result.document.xref_graph.edges.append(
            XrefGraphEdge(
                host_source_id=host_source.id,
                target_source_id=child_id,
                saved_path=raw_path,
                resolved_path=resolved_key,
                mode=mode,
                transform=transform,
                exists=True,
                parsed=False,
                composition_required=True,
            )
        )
        result.document.warnings.append(
            WarningRecord(
                code="xref-cycle",
                message=(
                    f"Recursive xref loop detected while resolving {resolved}. "
                    "Reference expansion stopped safely."
                ),
                severity="warning",
                source_id=host_source.id,
            )
        )

    # ------------------------------------------------------------------
    # Resolved xref
    # ------------------------------------------------------------------

    def _record_resolved(
        self,
        result: ParseResult,
        host_source: SourceDocument,
        child_id: str,
        raw_path: str | None,
        mode: XrefMode,
        transform: list | None,
        insertion_point: dict | None,
        candidates: list[Path],
        resolved: Path,
        depth: int,
        options: ParseOptions,
        visited: set[str],
    ) -> None:
        nested = self._parse_cached(resolved, options)
        nested_root = nested.document.root_source
        nested_root.id = child_id
        nested_root.role = "xref"
        nested_root.parent_source_id = host_source.id
        nested_root.xref_binding = XrefBindingMetadata(
            saved_path=raw_path,
            resolved_path=str(resolved),
            mode=mode,
            transform=transform,
            exists=True,
            parsed=nested_root.parsed,
            candidate_paths=[str(p) for p in candidates],
        )

        result.document.sources.append(nested_root)
        result.document.xref_graph.nodes.append(
            XrefGraphNode(
                source_id=child_id,
                path=raw_path or str(resolved),
                resolved_path=str(resolved),
                exists=True,
                parsed=nested_root.parsed,
                parse_status=nested_root.parse_status,
                parent_source_id=host_source.id,
                depth=depth + 1,
            )
        )
        result.document.xref_graph.edges.append(
            XrefGraphEdge(
                host_source_id=host_source.id,
                target_source_id=child_id,
                saved_path=raw_path,
                resolved_path=str(resolved),
                mode=mode,
                transform=transform,
                exists=True,
                parsed=nested_root.parsed,
                composition_required=True,
            )
        )

        # Recurse into the child's own xrefs
        self._resolve_for_source(
            result=result,
            host_source=nested_root,
            host_path=resolved,
            depth=depth + 1,
            visited=visited,
            options=options,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_cached(self, path: Path, options: ParseOptions) -> ParseResult:
        key = str(path.resolve())
        if key not in self._cache:
            self._cache[key] = self.backend.parse_xref(path, options)
        return self._cache[key]

    @staticmethod
    def _child_id(parent_id: str, index: int, raw_path: str | None) -> str:
        safe_name = (Path(raw_path).stem if raw_path else f"xref_{index}").replace(" ", "_")
        return f"{parent_id}__xref_{index}_{safe_name.lower()}"
