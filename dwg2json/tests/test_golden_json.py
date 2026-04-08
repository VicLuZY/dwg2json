"""Golden JSON tests — verify output structure matches expectations for known scenarios."""

import json
from pathlib import Path

from dwg2json.api import Dwg2JsonParser
from dwg2json.models import Entity, Layer, ParseOptions
from tests.conftest import FakeBackend

GOLDEN_DIR = Path(__file__).parent.parent / "examples" / "golden"


class TestGoldenSingleDwg:
    def test_structure(self, tmp_path: Path) -> None:
        root = tmp_path / "simple.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(
            entity_map={"simple": [
                Entity(
                    id="e1", source_id="src-simple", handle="1A", type="LINE",
                    layout="Model", space_class="model",
                ),
                Entity(
                    id="e2", source_id="src-simple", handle="1B", type="TEXT", text="Hello",
                    layout="Model", space_class="model",
                ),
            ]},
            layer_map={"simple": [
                Layer(id="l0", name="0"),
                Layer(id="l1", name="WALLS"),
            ]},
        )
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions(out_dir=str(tmp_path)))

        data = json.loads(Path(result.output_json_path).read_text())

        assert data["interpretation_status"] == "complete"
        assert data["completeness"]["status"] == "complete"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["role"] == "root"
        assert len(data["sources"][0]["entities"]) == 2
        assert len(data["sources"][0]["layers"]) == 2


class TestGoldenResolvedXref:
    def test_structure(self, tmp_path: Path) -> None:
        root = tmp_path / "host.dwg"
        root.write_bytes(b"\x00")
        bg = tmp_path / "bg.dwg"
        bg.write_bytes(b"\x00")

        t = [[1, 0, 100], [0, 1, 200], [0, 0, 1]]
        backend = FakeBackend(xref_map={
            "host": [{"path": "bg.dwg", "mode": "attach", "transform": t}],
        })
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions(out_dir=str(tmp_path)))

        data = json.loads(Path(result.output_json_path).read_text())

        assert data["interpretation_status"] == "complete"
        assert data["completeness"]["status"] == "complete"
        assert len(data["sources"]) == 2
        roles = {s["role"] for s in data["sources"]}
        assert roles == {"root", "xref"}
        assert len(data["xref_graph"]["edges"]) == 1
        assert data["xref_graph"]["edges"][0]["exists"] is True
        assert len(data["compositions"]) == 1
        assert data["compositions"][0]["completeness_status"] == "complete"


class TestGoldenMissingXref:
    def test_structure(self, tmp_path: Path) -> None:
        root = tmp_path / "device_layout.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={
            "device_layout": [{"path": "floor_plan.dwg", "mode": "overlay"}],
        })
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions(out_dir=str(tmp_path)))

        data = json.loads(Path(result.output_json_path).read_text())

        assert data["interpretation_status"] in ("partial", "degraded")
        assert data["completeness"]["status"] == "partial"
        assert data["completeness"]["missing_xrefs_count"] == 1
        assert data["completeness"]["consumer_caution"] is not None
        assert data["interpretation_confidence"]["value"] < 1.0

        missing_src = [s for s in data["sources"] if s["parse_status"] == "missing"]
        assert len(missing_src) == 1
        assert missing_src[0]["exists"] is False

        assert len(data["missing_references"]) == 1
        assert data["missing_references"][0]["kind"] == "xref"
        assert data["missing_references"][0]["interpretation_impacted"] is True

        comp = data["compositions"][0]
        assert comp["completeness_status"] == "missing_dependencies"
        assert len(comp["missing_source_ids"]) >= 1


class TestGoldenCycleXref:
    def test_structure(self, tmp_path: Path) -> None:
        a = tmp_path / "a.dwg"
        a.write_bytes(b"\x00")
        b = tmp_path / "b.dwg"
        b.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={
            "a": [{"path": "b.dwg"}],
            "b": [{"path": "a.dwg"}],
        })
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(a, ParseOptions(out_dir=str(tmp_path)))

        data = json.loads(Path(result.output_json_path).read_text())

        assert data["interpretation_status"] in ("partial", "degraded")
        cycle_warnings = [w for w in data["warnings"] if w["code"] == "xref-cycle"]
        assert len(cycle_warnings) >= 1

        unresolved = [s for s in data["sources"] if s["parse_status"] == "unresolved"]
        assert len(unresolved) >= 1
