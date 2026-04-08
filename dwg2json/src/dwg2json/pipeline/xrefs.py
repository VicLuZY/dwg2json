from __future__ import annotations

from pathlib import Path

from ..models import (
    ParseOptions,
    ParseResult,
    SourceDocument,
    WarningRecord,
    XrefBindingMetadata,
    XrefGraphEdge,
    XrefGraphNode,
)
from .xref_paths import resolve_candidate_paths


class XrefResolver:
    def __init__(self, backend) -> None:
        self.backend = backend
        self._cache: dict[str, ParseResult] = {}

    def resolve(self, result: ParseResult, options: ParseOptions) -> ParseResult:
        root_source = result.document.root_source
        root_path = Path(root_source.path)
        visited = {str(root_path.resolve()) if root_path.exists() else str(root_path)}
        self._resolve_for_source(
            result=result,
            host_source=root_source,
            host_path=root_path,
            depth=0,
            visited=visited,
            options=options,
        )
        return result

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
            return

        raw_xrefs = host_source.metadata.get("raw_xrefs", [])
        for index, raw in enumerate(raw_xrefs):
            raw_path = raw.get("path")
            mode = raw.get("mode", "unknown")
            transform = raw.get("transform")
            child_id = self._child_id(host_source.id, index, raw_path)
            candidates = resolve_candidate_paths(host_path.parent, raw_path)
            resolved = next((candidate for candidate in candidates if candidate.exists()), None)

            if resolved is None:
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
                        missing_reason="xref target not found on candidate paths",
                        candidate_paths=[str(path) for path in candidates],
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
                result.document.xref_graph_nodes.append(
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
                result.document.xref_graph_edges.append(
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
                result.document.warnings.append(
                    WarningRecord(
                        code="xref-missing",
                        message=f"Missing xref dependency prevents full composition: {raw_path}",
                        severity="warning",
                        source_id=host_source.id,
                    )
                )
                continue

            key = str(resolved.resolve())
            if key in visited:
                result.document.warnings.append(
                    WarningRecord(
                        code="xref-cycle",
                        message=f"Cycle detected while resolving {resolved}",
                        severity="warning",
                        source_id=host_source.id,
                    )
                )
                continue

            visited.add(key)
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
                candidate_paths=[str(path) for path in candidates],
            )
            result.document.sources.append(nested_root)
            result.document.xref_graph_nodes.append(
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
            result.document.xref_graph_edges.append(
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
            self._resolve_for_source(
                result=result,
                host_source=nested_root,
                host_path=resolved,
                depth=depth + 1,
                visited=visited,
                options=options,
            )

    def _parse_cached(self, path: Path, options: ParseOptions) -> ParseResult:
        key = str(path.resolve())
        if key not in self._cache:
            self._cache[key] = self.backend.parse_xref(path, options)
        return self._cache[key]

    @staticmethod
    def _child_id(parent_id: str, index: int, raw_path: str | None) -> str:
        safe_name = (Path(raw_path).stem if raw_path else f"xref_{index}").replace(" ", "_")
        return f"{parent_id}__xref_{index}_{safe_name.lower()}"
