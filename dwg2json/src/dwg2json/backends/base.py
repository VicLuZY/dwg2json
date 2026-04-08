from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import ParseOptions, ParseResult


class DwgBackend(ABC):
    name: str = "abstract"
    version: str | None = None

    @abstractmethod
    def parse(self, path: Path, options: ParseOptions) -> ParseResult:
        raise NotImplementedError

    def parse_xref(self, path: Path, options: ParseOptions) -> ParseResult:
        return self.parse(path, options)
