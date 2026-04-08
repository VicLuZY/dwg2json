"""Tests for completeness report computation."""

from pathlib import Path

from dwg2json.api import Dwg2JsonParser
from dwg2json.models import ParseOptions
from tests.conftest import FakeBackend


class TestCompletenessReport:
    def test_complete_no_xrefs(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions())

        cr = result.document.completeness
        assert cr.status == "complete"
        assert cr.missing_xrefs_count == 0
        assert cr.consumer_caution is None

    def test_partial_with_missing_xref(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={"root": [{"path": "missing.dwg"}]})
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        cr = result.document.completeness
        assert cr.status == "partial"
        assert cr.missing_xrefs_count == 1
        assert cr.consumer_caution is not None

    def test_complete_with_resolved_xref(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")
        bg = tmp_path / "bg.dwg"
        bg.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={"root": [{"path": "bg.dwg"}]})
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        assert result.document.completeness.status == "complete"

    def test_multiple_missing_xrefs(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={
            "root": [
                {"path": "bg1.dwg"},
                {"path": "bg2.dwg"},
            ],
        })
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        cr = result.document.completeness
        assert cr.status == "partial"
        assert cr.missing_xrefs_count == 2

    def test_mixed_resolved_and_missing(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")
        bg1 = tmp_path / "bg1.dwg"
        bg1.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={
            "root": [
                {"path": "bg1.dwg"},
                {"path": "missing.dwg"},
            ],
        })
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        cr = result.document.completeness
        assert cr.status == "partial"
        assert cr.missing_xrefs_count == 1

    def test_no_resolve_no_completeness_issues(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={"root": [{"path": "missing.dwg"}]})
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions(resolve_xrefs=False, bind_xrefs=False))

        assert result.document.completeness.status == "complete"
