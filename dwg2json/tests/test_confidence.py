"""Tests for interpretation confidence heuristics."""

from pathlib import Path

from dwg2json.api import Dwg2JsonParser
from dwg2json.models import ParseOptions
from tests.conftest import FakeBackend


class TestConfidence:
    def test_full_confidence_no_issues(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions())

        conf = result.document.interpretation_confidence
        assert conf.value >= 0.9

    def test_missing_xref_reduces_confidence(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={"root": [{"path": "missing.dwg"}]})
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        conf = result.document.interpretation_confidence
        assert conf.value < 1.0
        factor_names = [f.factor for f in conf.factors]
        assert "missing_xref" in factor_names

    def test_multiple_missing_xrefs_lower_more(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={
            "root": [
                {"path": "bg1.dwg"},
                {"path": "bg2.dwg"},
                {"path": "bg3.dwg"},
            ],
        })
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        conf = result.document.interpretation_confidence
        assert conf.value < 0.7

    def test_confidence_explanation_present(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions())

        assert result.document.interpretation_confidence.explanation is not None

    def test_cycle_reduces_confidence(self, tmp_path: Path) -> None:
        a = tmp_path / "a.dwg"
        a.write_bytes(b"\x00")
        b = tmp_path / "b.dwg"
        b.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={
            "a": [{"path": "b.dwg"}],
            "b": [{"path": "a.dwg"}],
        })
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(a, ParseOptions())

        conf = result.document.interpretation_confidence
        assert conf.value < 1.0
