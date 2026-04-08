"""Tests for xref resolution and binding — resolved and missing cases."""

from pathlib import Path

from dwg2json.api import Dwg2JsonParser
from dwg2json.models import Entity, ParseOptions
from tests.conftest import FakeBackend


class TestMissingXref:
    def test_missing_xref_marks_partial(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        identity_transform = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        backend = FakeBackend(
            xref_map={
                "root": [
                    {"path": "bg.dwg", "mode": "attach", "transform": identity_transform},
                ],
            },
        )
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions(resolve_xrefs=True, bind_xrefs=True))

        assert result.document.completeness.status == "partial"
        assert result.document.completeness.missing_xrefs_count == 1
        assert result.document.compositions[0].completeness_status == "missing_dependencies"
        assert result.document.compositions[0].missing_source_ids

    def test_missing_xref_produces_missing_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={"root": [{"path": "bg.dwg", "mode": "overlay"}]})
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        assert len(result.document.missing_references) == 1
        mr = result.document.missing_references[0]
        assert mr.kind == "xref"
        assert mr.requested_path == "bg.dwg"
        assert mr.interpretation_impacted

    def test_missing_xref_lowers_confidence(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={"root": [{"path": "bg.dwg"}]})
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        assert result.document.interpretation_confidence.value < 1.0

    def test_missing_xref_warnings(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={"root": [{"path": "bg.dwg"}]})
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        codes = [w.code for w in result.document.warnings]
        assert "xref-missing" in codes


class TestResolvedXref:
    def test_resolved_xref_is_complete(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")
        bg = tmp_path / "bg.dwg"
        bg.write_bytes(b"\x00")

        identity_transform = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        backend = FakeBackend(
            xref_map={
                "root": [
                    {"path": "bg.dwg", "mode": "attach", "transform": identity_transform},
                ],
            },
        )
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        assert result.document.completeness.status == "complete"
        assert len(result.document.sources) == 2
        assert result.document.compositions[0].completeness_status == "complete"

    def test_resolved_xref_entities_in_composition(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")
        bg = tmp_path / "bg.dwg"
        bg.write_bytes(b"\x00")

        backend = FakeBackend(
            xref_map={"root": [{"path": "bg.dwg", "mode": "attach"}]},
            entity_map={
                "root": [Entity(id="root-e1", source_id="src-root", handle="10", type="LINE")],
                "bg": [Entity(id="bg-e1", source_id="src-bg", handle="20", type="CIRCLE")],
            },
        )
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        comp = result.document.compositions[0]
        assert len(comp.entity_refs) >= 2

    def test_xref_graph_has_edge(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")
        bg = tmp_path / "bg.dwg"
        bg.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={"root": [{"path": "bg.dwg", "mode": "attach"}]})
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        assert len(result.document.xref_graph.edges) == 1
        edge = result.document.xref_graph.edges[0]
        assert edge.saved_path == "bg.dwg"
        assert edge.exists is True
