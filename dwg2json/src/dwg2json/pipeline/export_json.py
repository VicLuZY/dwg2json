"""Canonical JSON export with deterministic ordering."""

from __future__ import annotations

from pathlib import Path

import orjson

from ..models import DwgJsonDocument, ParseOptions, ParseResult


def _sort_document(doc: DwgJsonDocument) -> DwgJsonDocument:
    """Apply deterministic sorting rules to the document before serialisation.

    Rules (from development plan):
    - sources: by role (root first) then resolved_path then id
    - entities within each source: by handle then id
    - xref graph edges: by host_source_id then saved_path
    - compositions: by id
    """
    doc.sources.sort(key=lambda s: (0 if s.role == "root" else 1, s.resolved_path or "", s.id))
    for source in doc.sources:
        source.entities.sort(key=lambda e: (e.handle, e.id))
        source.layers.sort(key=lambda la: la.name)
        source.blocks.sort(key=lambda b: b.name)
    doc.xref_graph.nodes.sort(key=lambda n: (n.depth, n.source_id))
    doc.xref_graph.edges.sort(key=lambda e: (e.host_source_id, e.saved_path or ""))
    doc.compositions.sort(key=lambda c: c.id)
    doc.warnings.sort(key=lambda w: (w.severity, w.code, w.message))
    doc.missing_references.sort(key=lambda m: (m.parent_document_id or "", m.requested_path or ""))
    return doc


def to_json_text(result: ParseResult, indent: int = 2) -> str:
    doc = _sort_document(result.document)
    opts = orjson.OPT_SORT_KEYS
    if indent:
        opts |= orjson.OPT_INDENT_2
    return orjson.dumps(doc.model_dump(mode="json"), option=opts).decode()


def export_json_file(result: ParseResult, options: ParseOptions) -> Path:
    source_path = result.source_path
    output_dir = Path(options.out_dir) if options.out_dir else source_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{source_path.name}.json"
    output_path.write_text(to_json_text(result, indent=options.indent), encoding="utf-8")
    return output_path
