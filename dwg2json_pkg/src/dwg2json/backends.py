from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class BackendResult:
    raw_document: dict[str, Any]
    warnings: list[dict[str, Any]]
    backend_name: str
    backend_version: str | None = None


class BackendAdapter:
    name = "abstract"

    def parse(self, path: str) -> BackendResult:
        raise NotImplementedError


class NullBackendAdapter(BackendAdapter):
    name = "null"

    def parse(self, path: str) -> BackendResult:
        p = Path(path)
        return BackendResult(
            raw_document={
                "document_id": p.stem or "root",
                "source_file": str(p),
                "layers": [],
                "layouts": [],
                "block_definitions": [],
                "entities": [],
                "xref_requests": [],
            },
            warnings=[
                {
                    "code": "NO_BACKEND",
                    "message": "No native DWG backend configured. This is a seed scaffold only.",
                    "severity": "warning",
                    "related_paths": [str(p)],
                }
            ],
            backend_name=self.name,
            backend_version=None,
        )
