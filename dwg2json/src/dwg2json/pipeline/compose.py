"""Composition builder — binds host and xref content into shared spatial contexts.

A composition is the minimum interpretable spatial grouping where host
drawing content and resolved xref content coexist in the same coordinate
frame.  Transform chains are propagated so downstream consumers can
reconstruct the placed geometry.
"""

from __future__ import annotations

from ..models import (
    Composition,
    ParseOptions,
    ParseResult,
    SourceBinding,
    SourceDocument,
)


class CompositionBuilder:
    def bind(self, result: ParseResult, options: ParseOptions) -> ParseResult:
        document = result.document
        root = document.root_source

        composition = Composition(
            id=f"composition-{root.id}",
            name=f"Composed context for {root.path}",
            root_source_id=root.id,
            layout_name="Model",
        )

        entity_refs: list[str] = []
        missing_source_ids: list[str] = []

        # Build a parent -> source lookup for transform chain propagation
        source_by_id: dict[str, SourceDocument] = {s.id: s for s in document.sources}

        for source in document.sources:
            transform_chain = self._build_transform_chain(source, source_by_id)
            placement_transform = (
                source.xref_binding.transform if source.xref_binding else None
            )
            is_missing = not source.exists or source.parse_status in {
                "missing",
                "unresolved",
                "failed",
            }

            binding = SourceBinding(
                source_id=source.id,
                parent_source_id=source.parent_source_id,
                placement_transform=placement_transform,
                inherited_transform_chain=transform_chain,
                mode=source.xref_binding.mode if source.xref_binding else "unknown",
                included_entity_ids=[e.id for e in source.entities],
                missing_dependency=is_missing,
            )
            composition.source_bindings.append(binding)
            entity_refs.extend(binding.included_entity_ids)

            if is_missing:
                missing_source_ids.append(source.id)

        composition.entity_refs = sorted(entity_refs)
        composition.missing_source_ids = sorted(set(missing_source_ids))

        if composition.missing_source_ids:
            composition.completeness_status = "missing_dependencies"
            composition.notes.append(
                "One or more bound xref dependencies were missing or unresolved. "
                "Geometric interpretation is partial."
            )
        else:
            composition.completeness_status = "complete"

        document.compositions = [composition]
        return result

    @staticmethod
    def _build_transform_chain(
        source: SourceDocument,
        source_by_id: dict[str, SourceDocument],
    ) -> list[list[list[float]]]:
        """Walk up the parent chain collecting placement transforms."""
        chain: list[list[list[float]]] = []
        current = source
        while current.parent_source_id and current.xref_binding:
            if current.xref_binding.transform:
                chain.append(current.xref_binding.transform)
            parent = source_by_id.get(current.parent_source_id)
            if parent is None:
                break
            current = parent
        chain.reverse()
        return chain
