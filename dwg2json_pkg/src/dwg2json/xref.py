from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ResolvedReference:
    requested_path: str
    normalized_path: str
    absolute_path: Path | None
    status: str


class XrefResolver:
    def __init__(self, search_roots: list[str] | None = None) -> None:
        self.search_roots = [Path(p) for p in (search_roots or [])]

    def resolve(self, requested_path: str, current_document_path: str | None = None) -> ResolvedReference:
        candidates: list[Path] = []
        req = Path(requested_path)

        if req.is_absolute():
            candidates.append(req)
        else:
            if current_document_path:
                candidates.append(Path(current_document_path).parent / req)
            for root in self.search_roots:
                candidates.append(root / req)

        for candidate in candidates:
            if candidate.exists():
                return ResolvedReference(
                    requested_path=requested_path,
                    normalized_path=str(req),
                    absolute_path=candidate.resolve(),
                    status="resolved",
                )

        return ResolvedReference(
            requested_path=requested_path,
            normalized_path=str(req),
            absolute_path=None,
            status="missing",
        )
