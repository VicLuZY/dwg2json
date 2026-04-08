from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .backends import BackendAdapter, NullBackendAdapter
from .models import (
    CanonicalDrawingDocument,
    CompositeContext,
    MissingReference,
    ParseWarning,
    Provenance,
    XrefBinding,
)
from .xref import XrefResolver


class Dwg2JsonParser:
    def __init__(
        self,
        backend: BackendAdapter | None = None,
        xref_search_roots: list[str] | None = None,
    ) -> None:
        self.backend = backend or NullBackendAdapter()
        self.xref_resolver = XrefResolver(search_roots=xref_search_roots)

    def parse_file(self, path: str) -> CanonicalDrawingDocument:
        backend_result = self.backend.parse(path)
        raw = backend_result.raw_document

        doc = CanonicalDrawingDocument(
            root_document_id=raw.get("document_id", Path(path).stem or "root"),
            document_metadata={"source_file": str(Path(path))},
            provenance=Provenance(
                backend_name=backend_result.backend_name,
                backend_version=backend_result.backend_version,
                source_file=str(Path(path)),
                parse_timestamp_utc=datetime.now(timezone.utc).isoformat(),
            ),
            warnings=[ParseWarning(**w) for w in backend_result.warnings],
            interpretation_confidence=0.15,
            interpretation_status="degraded",
        )

        xref_requests = raw.get("xref_requests", [])
        for i, req in enumerate(xref_requests):
            requested_path = req.get("path", "")
            resolved = self.xref_resolver.resolve(requested_path, current_document_path=path)
            xref_id = f"xref:{i}"
            if resolved.status == "resolved":
                doc.xrefs.append(
                    XrefBinding(
                        id=xref_id,
                        host_document_id=doc.root_document_id,
                        referenced_document_id=req.get("document_id"),
                        block_reference_entity_id=req.get("host_entity_id"),
                        requested_path=requested_path,
                        resolved_path=str(resolved.absolute_path) if resolved.absolute_path else None,
                        status="resolved",
                        overlay_mode=req.get("overlay_mode", "unknown"),
                        interpretation_notes=[
                            "Referenced drawing should be interpreted in host composition, not in isolation."
                        ],
                    )
                )
            else:
                doc.xrefs.append(
                    XrefBinding(
                        id=xref_id,
                        host_document_id=doc.root_document_id,
                        referenced_document_id=None,
                        block_reference_entity_id=req.get("host_entity_id"),
                        requested_path=requested_path,
                        resolved_path=None,
                        status="missing",
                        overlay_mode=req.get("overlay_mode", "unknown"),
                        interpretation_notes=[
                            "Referenced drawing unavailable. Composite spatial interpretation is incomplete."
                        ],
                    )
                )
                doc.missing_references.append(
                    MissingReference(
                        kind="xref",
                        requested_path=requested_path,
                        normalized_path=resolved.normalized_path,
                        resolver_root=str(Path(path).parent),
                        parent_document_id=doc.root_document_id,
                        host_handles=[h for h in [req.get("host_handle")] if h],
                        impact_summary=(
                            "A referenced drawing required for composite interpretation was missing. "
                            "Entities hosted against this xref may not be interpretable in full geometric context."
                        ),
                        severity="warning",
                        interpretation_impacted=True,
                    )
                )

        doc.composite_contexts.append(
            CompositeContext(
                id=f"composite:{doc.root_document_id}:default",
                host_document_id=doc.root_document_id,
                participating_document_ids=[doc.root_document_id]
                + [x.referenced_document_id for x in doc.xrefs if x.referenced_document_id],
                participating_xref_ids=[x.id for x in doc.xrefs],
                interpretation_required=True,
                summary=(
                    "Default composite context for host drawing and all interpretable xrefs. "
                    "Overlay-hosted geometry should be analyzed together with referenced backgrounds."
                ),
            )
        )

        if doc.missing_references:
            doc.interpretation_status = "partial"
            doc.interpretation_confidence = 0.55 if len(doc.missing_references) < len(doc.xrefs) else 0.35
            doc.warnings.append(
                ParseWarning(
                    code="MISSING_XREFS",
                    message="One or more xrefs were missing. Interpret geometric relationships with caution.",
                    severity="warning",
                    related_paths=[m.requested_path or "" for m in doc.missing_references if m.requested_path],
                )
            )
        elif doc.xrefs:
            doc.interpretation_status = "partial"
            doc.interpretation_confidence = 0.7
        return doc

    def parse_to_json_text(self, path: str, indent: int = 2) -> str:
        return self.parse_file(path).model_dump_json(indent=indent)

    def parse_to_json_file(self, input_path: str, output_path: str | None = None, indent: int = 2) -> str:
        output = output_path or f"{input_path}.json"
        Path(output).write_text(self.parse_to_json_text(input_path, indent=indent), encoding="utf-8")
        return output
