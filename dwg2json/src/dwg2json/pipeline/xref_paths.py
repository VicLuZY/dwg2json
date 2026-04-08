from __future__ import annotations

from pathlib import Path


def resolve_candidate_paths(base_dir: Path, raw_path: str | None) -> list[Path]:
    if not raw_path:
        return []

    candidate = Path(raw_path)
    candidates: list[Path] = []

    if candidate.is_absolute():
        candidates.append(candidate)
    else:
        candidates.append(base_dir / candidate)
        candidates.append((base_dir / candidate.name).resolve())

    seen: set[str] = set()
    unique: list[Path] = []
    for item in candidates:
        key = str(item)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique
