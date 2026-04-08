"""Tests for the composition builder."""

from pathlib import Path

from dwg2json.api import Dwg2JsonParser
from dwg2json.models import Entity, ParseOptions
from tests.conftest import FakeBackend


class TestCompositionBuilder:
    def test_single_source_composition(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions())

        assert len(result.document.compositions) == 1
        comp = result.document.compositions[0]
        assert comp.root_source_id == "src-root"
        assert comp.completeness_status == "complete"
        assert len(comp.source_bindings) == 1

    def test_resolved_xref_composition(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")
        bg = tmp_path / "bg.dwg"
        bg.write_bytes(b"\x00")

        transform = [[1, 0, 10], [0, 1, 20], [0, 0, 1]]
        backend = FakeBackend(xref_map={
            "root": [{"path": "bg.dwg", "mode": "overlay", "transform": transform}],
        })
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        comp = result.document.compositions[0]
        assert comp.completeness_status == "complete"
        assert len(comp.source_bindings) == 2

        xref_binding = [b for b in comp.source_bindings if b.source_id != "src-root"][0]
        assert xref_binding.placement_transform == transform
        assert xref_binding.mode == "overlay"
        assert not xref_binding.missing_dependency

    def test_transform_chain_propagation(self, tmp_path: Path) -> None:
        """Nested xrefs should accumulate transform chains."""
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")
        mid = tmp_path / "mid.dwg"
        mid.write_bytes(b"\x00")
        leaf = tmp_path / "leaf.dwg"
        leaf.write_bytes(b"\x00")

        t1 = [[1, 0, 10], [0, 1, 0], [0, 0, 1]]
        t2 = [[1, 0, 0], [0, 1, 20], [0, 0, 1]]

        backend = FakeBackend(xref_map={
            "root": [{"path": "mid.dwg", "mode": "attach", "transform": t1}],
            "mid": [{"path": "leaf.dwg", "mode": "attach", "transform": t2}],
        })
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        comp = result.document.compositions[0]
        leaf_bindings = [b for b in comp.source_bindings if "leaf" in b.source_id]
        assert len(leaf_bindings) == 1
        chain = leaf_bindings[0].inherited_transform_chain
        assert len(chain) == 2

    def test_missing_xref_in_composition(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={"root": [{"path": "missing.dwg"}]})
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        comp = result.document.compositions[0]
        assert comp.completeness_status == "missing_dependencies"
        assert len(comp.missing_source_ids) >= 1
        assert any("missing" in sid for sid in comp.missing_source_ids)

    def test_entity_refs_collected(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(entity_map={
            "root": [
                Entity(id="e1", source_id="src-root", handle="10", type="LINE"),
                Entity(id="e2", source_id="src-root", handle="20", type="CIRCLE"),
            ],
        })
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        comp = result.document.compositions[0]
        assert "e1" in comp.entity_refs
        assert "e2" in comp.entity_refs
