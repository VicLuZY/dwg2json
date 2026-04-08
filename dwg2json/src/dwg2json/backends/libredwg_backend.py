from __future__ import annotations

from pathlib import Path

from ..models import (
    DwgJsonDocument,
    ParseOptions,
    ParseResult,
    ParserInfo,
    SourceDocument,
    WarningRecord,
    XrefGraphNode,
)
from .base import DwgBackend


class LibreDwgBackend(DwgBackend):
    name = "libredwg"
    version = None

    def parse(self, path: Path, options: ParseOptions) -> ParseResult:
        root_id = self._source_id(path)
        root_warning = WarningRecord(
            code="seed-backend",
            message=(
                "No production DWG decoder is wired yet. This seed package only defines the architecture, canonical JSON schema, and xref composition flow."
            ),
            severity="warning",
            source_id=root_id,
        )
        root_source = SourceDocument(
            id=root_id,
            path=str(path),
            resolved_path=str(path.resolve()) if path.exists() else None,
            role="root",
            exists=path.exists(),
            parsed=path.exists(),
            parse_status="parsed" if path.exists() else "failed",
            metadata={
                "status": "seed-backend",
                "note": "Implement real LibreDWG bridge here.",
                "raw_xrefs": [],
            },
            warnings=[root_warning],
        )
        document = DwgJsonDocument(
            parser=ParserInfo(name="dwg2json", version="0.1.0a0", backend=self.name, backend_version=self.version),
            root_source_id=root_id,
            sources=[root_source],
            xref_graph_nodes=[
                XrefGraphNode(
                    source_id=root_id,
                    path=str(path),
                    resolved_path=str(path.resolve()) if path.exists() else None,
                    exists=path.exists(),
                    parsed=path.exists(),
                    parse_status=root_source.parse_status,
                    depth=0,
                )
            ],
            warnings=[root_warning],
        )
        return ParseResult(document=document)

    @staticmethod
    def _source_id(path: Path) -> str:
        stem = path.stem.replace(" ", "_") or "drawing"
        return f"src-{stem.lower()}"
