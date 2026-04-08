"""Abstract backend interface.

Every DWG decoder backend must subclass ``DwgBackend`` and implement
``parse``.  The backend is responsible for producing a
``ParseResult`` containing a single ``DwgJsonDocument`` with the root
source populated (entities, layers, blocks, layouts, warnings, and
raw xref declarations in ``metadata["raw_xrefs"]``).

The xref resolution, composition, and confidence steps are handled by
the pipeline *after* the backend returns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import ParseOptions, ParseResult


class DwgBackend(ABC):
    name: str = "abstract"
    version: str | None = None

    @abstractmethod
    def parse(self, path: Path, options: ParseOptions) -> ParseResult:
        """Parse a DWG file and return a single-source ParseResult."""
        raise NotImplementedError

    def parse_xref(self, path: Path, options: ParseOptions) -> ParseResult:
        """Parse an xref child DWG.  Defaults to the same logic as ``parse``."""
        return self.parse(path, options)

    def is_available(self) -> bool:
        """Return True if this backend's runtime dependencies are satisfied."""
        return True
