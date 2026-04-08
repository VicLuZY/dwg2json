"""Tests for xref cycle detection."""

from pathlib import Path

from dwg2json.api import Dwg2JsonParser
from dwg2json.models import ParseOptions
from tests.conftest import FakeBackend


class TestXrefCycleDetection:
    def test_direct_cycle(self, tmp_path: Path) -> None:
        """A references B which references A — cycle should be detected."""
        a = tmp_path / "a.dwg"
        a.write_bytes(b"\x00")
        b = tmp_path / "b.dwg"
        b.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={
            "a": [{"path": "b.dwg", "mode": "attach"}],
            "b": [{"path": "a.dwg", "mode": "attach"}],
        })
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(a, ParseOptions())

        # Should not hang or recurse infinitely
        codes = [w.code for w in result.document.warnings]
        assert "xref-cycle" in codes

        # The cycle-blocked source should exist as unresolved
        cycle_sources = [
            s for s in result.document.sources
            if s.role == "xref" and s.parse_status == "unresolved"
        ]
        assert len(cycle_sources) >= 1

    def test_self_reference_cycle(self, tmp_path: Path) -> None:
        """A references itself."""
        a = tmp_path / "a.dwg"
        a.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={"a": [{"path": "a.dwg", "mode": "attach"}]})
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(a, ParseOptions())

        codes = [w.code for w in result.document.warnings]
        assert "xref-cycle" in codes

    def test_transitive_cycle(self, tmp_path: Path) -> None:
        """A → B → C → A — three-node cycle."""
        for name in ("a", "b", "c"):
            (tmp_path / f"{name}.dwg").write_bytes(b"\x00")

        backend = FakeBackend(xref_map={
            "a": [{"path": "b.dwg"}],
            "b": [{"path": "c.dwg"}],
            "c": [{"path": "a.dwg"}],
        })
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(tmp_path / "a.dwg", ParseOptions())

        codes = [w.code for w in result.document.warnings]
        assert "xref-cycle" in codes

    def test_depth_limit(self, tmp_path: Path) -> None:
        """Long chain exceeding max depth."""
        depth = 5
        for i in range(depth + 2):
            (tmp_path / f"d{i}.dwg").write_bytes(b"\x00")

        xref_map = {f"d{i}": [{"path": f"d{i+1}.dwg"}] for i in range(depth + 1)}
        backend = FakeBackend(xref_map=xref_map)
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(tmp_path / "d0.dwg", ParseOptions(max_xref_depth=depth))

        codes = [w.code for w in result.document.warnings]
        assert "xref-depth-limit" in codes

    def test_cycle_does_not_crash_composition(self, tmp_path: Path) -> None:
        """Cycle-blocked xrefs should still produce valid compositions."""
        a = tmp_path / "a.dwg"
        a.write_bytes(b"\x00")
        b = tmp_path / "b.dwg"
        b.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={
            "a": [{"path": "b.dwg"}],
            "b": [{"path": "a.dwg"}],
        })
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(a, ParseOptions(resolve_xrefs=True, bind_xrefs=True))

        assert len(result.document.compositions) == 1
        assert result.document.completeness.status in ("partial", "incomplete")
