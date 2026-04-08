from pathlib import Path

from dwg2json.pipeline.xref_paths import resolve_candidate_paths


def test_relative_path_candidates(tmp_path: Path) -> None:
    candidates = resolve_candidate_paths(tmp_path, "refs/site.dwg")
    assert any("site.dwg" in str(path) for path in candidates)
