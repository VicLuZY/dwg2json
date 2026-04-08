"""Publication semantics: paper vs model indexing and LLM-friendly navigation hints."""

from __future__ import annotations

from ..models import ParseOptions, PublicationIndexEntry, SourceDocument


def enrich_source_publication(source: SourceDocument, options: ParseOptions) -> None:
    """Fill layout paper-space indexes, interpretation notes, and publication_index."""
    if not source.parsed:
        return

    model_entity_count = sum(
        1
        for e in source.entities
        if e.layout == "Model" or (e.space_class == "model")
    )

    for layout in source.layouts:
        if layout.is_model_space:
            layout.paper_space_entity_ids = []
            continue
        paper_ids: list[str] = []
        for ent in source.entities:
            if ent.layout != layout.name:
                continue
            if ent.space_class == "paper" or ent.space_class is None:
                paper_ids.append(ent.id)
        layout.paper_space_entity_ids = sorted(set(paper_ids))

        notes = list(layout.interpretation_notes)
        vp_n = len(layout.viewports)
        if vp_n == 0 and model_entity_count > 0:
            notes.append(
                "This sheet has no paper-space viewports into model space; "
                "model geometry may appear only on other layouts or not at all on paper output."
            )
        if model_entity_count > 100 and vp_n > 0:
            notes.append(
                "Model space contains many entities; what appears on this sheet depends on "
                "viewport framing and per-viewport layer freeze state."
            )
        layout.interpretation_notes = notes

    if not options.emit_publication_index:
        source.publication_index = []
        return

    entries: list[PublicationIndexEntry] = []

    if any(ly.name == "Model" for ly in source.layouts):
        entries.append(
            PublicationIndexEntry(
                layout_name="Model",
                viewport_record_id=None,
                role="authoring_model",
                notes=[
                    "Full model-space entity list in sources[].entities with layout Model.",
                    (
                        'CAD users often say "sheet" for a layout tab; '
                        "this JSON uses each layout's stored name."
                    ),
                    (
                        "Sheet Set Manager (.dst) is external to the DWG; use layouts here "
                        "plus sidecar files for project-level sheet lists."
                    ),
                ],
            )
        )

    for layout in sorted(source.layouts, key=lambda ly: (ly.tab_order, ly.name)):
        if layout.is_model_space:
            continue
        entries.append(
            PublicationIndexEntry(
                layout_name=layout.name,
                viewport_record_id=None,
                role="sheet",
                notes=[
                    (
                        f"{len(layout.paper_space_entity_ids)} paper-space entities "
                        "on this layout."
                    ),
                ],
            )
        )
        for vp in sorted(layout.viewports, key=lambda v: v.handle):
            role = "layout_tab_viewport" if (vp.viewport_dxf_id == 1) else "model_view"
            entries.append(
                PublicationIndexEntry(
                    layout_name=layout.name,
                    viewport_record_id=vp.id,
                    role=role,
                    notes=[],
                )
            )

    source.publication_index = entries
