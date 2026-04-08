"""Tests for xref path candidate resolution."""

from pathlib import Path

from dwg2json.pipeline.xref_paths import normalize_xref_path, resolve_candidate_paths


class TestResolveCandidatePaths:
    def test_empty_path(self) -> None:
        assert resolve_candidate_paths(Path("/tmp"), None) == []
        assert resolve_candidate_paths(Path("/tmp"), "") == []

    def test_relative_path(self, tmp_path: Path) -> None:
        candidates = resolve_candidate_paths(tmp_path, "refs/site.dwg")
        assert len(candidates) >= 1
        assert any("site.dwg" in str(p) for p in candidates)

    def test_absolute_path(self, tmp_path: Path) -> None:
        target = tmp_path / "absolute.dwg"
        candidates = resolve_candidate_paths(tmp_path, str(target))
        assert target.resolve() in [c.resolve() for c in candidates]

    def test_filename_only_in_host_dir(self, tmp_path: Path) -> None:
        candidates = resolve_candidate_paths(tmp_path, "sub/dir/drawing.dwg")
        names = [c.name for c in candidates]
        assert "drawing.dwg" in names

    def test_search_roots(self, tmp_path: Path) -> None:
        search_dir = tmp_path / "xrefs"
        search_dir.mkdir()
        candidates = resolve_candidate_paths(
            tmp_path, "bg.dwg", search_roots=[str(search_dir)]
        )
        assert any(str(search_dir) in str(c) for c in candidates)

    def test_deduplication(self, tmp_path: Path) -> None:
        candidates = resolve_candidate_paths(
            tmp_path, "same.dwg", search_roots=[str(tmp_path)]
        )
        paths_str = [str(c) for c in candidates]
        assert len(paths_str) == len(set(paths_str))

    def test_multiple_search_roots(self, tmp_path: Path) -> None:
        root1 = tmp_path / "root1"
        root2 = tmp_path / "root2"
        root1.mkdir()
        root2.mkdir()
        candidates = resolve_candidate_paths(
            tmp_path, "bg.dwg", search_roots=[str(root1), str(root2)]
        )
        root1_found = any(str(root1) in str(c) for c in candidates)
        root2_found = any(str(root2) in str(c) for c in candidates)
        assert root1_found and root2_found


class TestNormalizeXrefPath:
    def test_backslash_to_forward(self) -> None:
        assert "/" in normalize_xref_path("refs\\bg.dwg")

    def test_redundant_separators(self) -> None:
        result = normalize_xref_path("refs//bg.dwg")
        assert "//" not in result

    def test_identity(self) -> None:
        assert normalize_xref_path("bg.dwg") == "bg.dwg"
