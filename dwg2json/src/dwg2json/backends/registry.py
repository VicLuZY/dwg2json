"""Backend registry — resolves a backend name to a concrete instance."""

from __future__ import annotations

from .base import DwgBackend
from .libredwg_backend import LibreDwgBackend
from .null_backend import NullBackend

_REGISTRY: dict[str, type[DwgBackend]] = {
    "libredwg": LibreDwgBackend,
    "null": NullBackend,
}


def get_backend(name: str = "auto") -> DwgBackend:
    """Return an instantiated backend.

    ``"auto"`` tries LibreDWG first, falling back to null if LibreDWG
    is not available on the system.
    """
    if name == "auto":
        backend = LibreDwgBackend()
        if backend.is_available():
            return backend
        return NullBackend()

    cls = _REGISTRY.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown backend {name!r}. Available: {sorted(_REGISTRY)} or 'auto'."
        )
    return cls()
