"""Null backend — returns structurally valid but empty results.

Used for testing the pipeline, schema validation, and development
without requiring a real DWG decoder.
"""

from __future__ import annotations

from pathlib import Path

from ..models import (
    DwgJsonDocument,
    Layout,
    ParseOptions,
    ParseResult,
    ParserInfo,
    SourceDocument,
    WarningRecord,
    XrefGraphNode,
)
from .base import DwgBackend


class NullBackend(DwgBackend):
    name = "null"
    version = "0.1.0"

    def parse(self, path: Path, options: ParseOptions) -> ParseResult:
        root_id = self._source_id(path)
        exists = path.exists()

        source = SourceDocument(
            id=root_id,
            path=str(path),
            resolved_path=str(path.resolve()) if exists else None,
            role="root",
            exists=exists,
            parsed=exists,
            parse_status="parsed" if exists else "failed",
            metadata={"raw_xrefs": [], "backend": "null"},
            layouts=[
                Layout(id=f"{root_id}__model", name="Model", is_model_space=True, tab_order=0),
            ],
            warnings=[
                WarningRecord(
                    code="null-backend",
                    message="Null backend produces structurally valid but empty results.",
                    severity="info",
                    source_id=root_id,
                ),
            ],
        )

        document = DwgJsonDocument(
            parser=ParserInfo(
                backend=self.name,
                backend_version=self.version,
            ),
            root_source_id=root_id,
            sources=[source],
        )
        document.xref_graph.nodes.append(
            XrefGraphNode(
                source_id=root_id,
                path=str(path),
                resolved_path=str(path.resolve()) if exists else None,
                exists=exists,
                parsed=exists,
                parse_status=source.parse_status,
                depth=0,
            )
        )
        return ParseResult(document=document)

    @staticmethod
    def _source_id(path: Path) -> str:
        stem = path.stem.replace(" ", "_") or "drawing"
        return f"src-{stem.lower()}"
