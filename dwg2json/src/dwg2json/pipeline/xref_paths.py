"""Xref path candidate resolution.

Implements the dependency-resolution search order specified in the
development plan:

1. Absolute path (if the saved path is absolute).
2. Relative to the host DWG's directory.
3. Configured xref search roots.
4. Filename-only fallback in the host directory.

All attempted paths are returned so the caller can record them for
debugging and provenance.
"""

from __future__ import annotations

import os
from pathlib import Path


def resolve_candidate_paths(
    base_dir: Path,
    raw_path: str | None,
    search_roots: list[str] | list[Path] | None = None,
) -> list[Path]:
    """Return an ordered list of candidate file-system paths for *raw_path*.

    Duplicates (by resolved string) are removed while preserving priority
    order.
    """
    if not raw_path:
        return []

    candidate = Path(raw_path)
    candidates: list[Path] = []

    if candidate.is_absolute():
        candidates.append(candidate)
    else:
        candidates.append((base_dir / candidate).resolve())

    # Filename-only in the host directory
    candidates.append((base_dir / candidate.name).resolve())

    # Search roots
    for root in search_roots or []:
        root_path = Path(root)
        candidates.append((root_path / candidate).resolve())
        candidates.append((root_path / candidate.name).resolve())

    # De-duplicate while preserving order
    seen: set[str] = set()
    unique: list[Path] = []
    for item in candidates:
        key = str(item)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def normalize_xref_path(raw_path: str) -> str:
    """Normalize a raw xref path for deterministic comparison.

    Backslashes are converted to forward slashes and redundant separators
    are collapsed.  No filesystem access is performed.
    """
    return os.path.normpath(raw_path).replace("\\", "/")
