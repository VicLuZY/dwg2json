"""Tests for JSON export and determinism."""

import json
from pathlib import Path

from dwg2json.api import Dwg2JsonParser
from dwg2json.models import ParseOptions
from tests.conftest import FakeBackend


class TestJsonExport:
    def test_exports_single_json_file(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")
        out_dir = tmp_path / "out"

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions(out_dir=str(out_dir)))

        assert result.output_json_path is not None
        p = Path(result.output_json_path)
        assert p.exists()
        assert p.name == "root.dwg.json"

    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")
        out_dir = tmp_path / "out"

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions(out_dir=str(out_dir)))

        data = json.loads(Path(result.output_json_path).read_text())
        assert data["schema_version"] == "0.2.0"
        assert data["root_source_id"] == "src-root"

    def test_output_has_required_top_level_keys(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")
        out_dir = tmp_path / "out"

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions(out_dir=str(out_dir)))

        data = json.loads(Path(result.output_json_path).read_text())
        required_keys = {
            "schema_version", "parser", "root_source_id", "sources",
            "xref_graph", "compositions", "completeness",
            "interpretation_confidence", "interpretation_status",
            "missing_references", "warnings", "metadata",
        }
        assert required_keys.issubset(data.keys())

    def test_to_json_text(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions())

        text = result.to_json_text()
        data = json.loads(text)
        assert data["schema_version"] == "0.2.0"

    def test_write_json_file_method(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")
        out_dir = tmp_path / "out"

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions())

        path = result.write_json_file(out_dir)
        assert path.exists()
        data = json.loads(path.read_text())
        assert "sources" in data


class TestDeterminism:
    def test_repeated_parse_same_json(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={"root": [{"path": "missing.dwg"}]})
        parser = Dwg2JsonParser(backend=backend)

        r1 = parser.parse(root, ParseOptions())
        r2 = parser.parse(root, ParseOptions())

        t1 = r1.to_json_text()
        t2 = r2.to_json_text()

        d1 = json.loads(t1)
        d2 = json.loads(t2)

        # Remove timestamps which will differ
        d1["parser"].pop("timestamp", None)
        d2["parser"].pop("timestamp", None)

        assert d1 == d2

    def test_sources_sorted_deterministically(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")
        bg = tmp_path / "bg.dwg"
        bg.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={"root": [{"path": "bg.dwg"}]})
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions(out_dir=str(tmp_path / "out")))

        data = json.loads(Path(result.output_json_path).read_text())
        roles = [s["role"] for s in data["sources"]]
        assert roles[0] == "root"

    def test_warnings_sorted(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions(out_dir=str(tmp_path / "out")))

        data = json.loads(Path(result.output_json_path).read_text())
        severities = [w["severity"] for w in data["warnings"]]
        assert severities == sorted(severities)
