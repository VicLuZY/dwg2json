from __future__ import annotations

from ..models import Composition, ParseOptions, ParseResult, SourceBinding


class CompositionBuilder:
    def bind(self, result: ParseResult, options: ParseOptions) -> ParseResult:
        document = result.document
        root = document.root_source
        composition = Composition(
            id=f"composition-{root.id}",
            name=f"Composed context for {root.path}",
            root_source_id=root.id,
            layout_name=None,
        )

        entity_refs: list[str] = []
        missing_source_ids: list[str] = []

        for source in document.sources:
            binding = SourceBinding(
                source_id=source.id,
                parent_source_id=source.parent_source_id,
                placement_transform=source.xref_binding.transform if source.xref_binding else None,
                inherited_transform_chain=(
                    [source.xref_binding.transform] if source.xref_binding and source.xref_binding.transform else []
                ),
                mode=source.xref_binding.mode if source.xref_binding else "unknown",
                included_entity_ids=[entity.id for entity in source.entities],
                missing_dependency=not source.exists or source.parse_status in {"missing", "unresolved", "failed"},
            )
            composition.source_bindings.append(binding)
            entity_refs.extend(binding.included_entity_ids)
            if binding.missing_dependency:
                missing_source_ids.append(source.id)

        composition.entity_refs = sorted(entity_refs)
        composition.missing_source_ids = sorted(set(missing_source_ids))
        if composition.missing_source_ids:
            composition.completeness_status = "missing_dependencies"
            composition.notes.append(
                "One or more bound xref dependencies were missing or unresolved. Geometric interpretation is partial."
            )
        else:
            composition.completeness_status = "complete"

        document.compositions = [composition]
        return result
