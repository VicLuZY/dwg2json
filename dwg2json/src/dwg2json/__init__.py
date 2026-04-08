"""dwg2json — DWG to canonical JSON deparser with xref-bound composition semantics."""

from .api import Dwg2JsonParser
from .models import (
    DwgJsonDocument,
    ParseOptions,
    ParseResult,
)

__version__ = "0.2.0"

__all__ = [
    "Dwg2JsonParser",
    "DwgJsonDocument",
    "ParseOptions",
    "ParseResult",
    "__version__",
]
