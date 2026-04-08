"""Tests for the public API (Dwg2JsonParser)."""

import json
from pathlib import Path

from dwg2json.api import Dwg2JsonParser
from dwg2json.models import ParseOptions
from tests.conftest import FakeBackend


class TestDwg2JsonParser:
    def test_default_backend(self) -> None:
        parser = Dwg2JsonParser()
        assert parser.backend is not None

    def test_string_backend(self) -> None:
        parser = Dwg2JsonParser(backend="null")
        assert parser.backend.name == "null"

    def test_instance_backend(self) -> None:
        backend = FakeBackend()
        parser = Dwg2JsonParser(backend=backend)
        assert parser.backend is backend

    def test_parse(self, tmp_path: Path) -> None:
        root = tmp_path / "test.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root)

        assert result.document.root_source_id == "src-test"
        assert result.document.schema_version == "0.1.0"

    def test_parse_with_options(self, tmp_path: Path) -> None:
        root = tmp_path / "test.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions(resolve_xrefs=False, bind_xrefs=False))

        assert len(result.document.compositions) == 0

    def test_parse_sets_interpretation_status(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions())

        assert result.document.interpretation_status in (
            "complete",
            "partial",
            "degraded",
            "failed",
        )

    def test_parse_records_options_in_metadata(self, tmp_path: Path) -> None:
        root = tmp_path / "test.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions(max_xref_depth=5))

        assert "parser_options" in result.document.metadata
        assert result.document.metadata["parser_options"]["max_xref_depth"] == 5


class TestConvenienceMethods:
    def test_parse_file(self, tmp_path: Path) -> None:
        root = tmp_path / "test.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        doc = parser.parse_file(root)

        assert doc.root_source_id == "src-test"
        assert doc.schema_version == "0.1.0"

    def test_parse_to_json_text(self, tmp_path: Path) -> None:
        root = tmp_path / "test.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        text = parser.parse_to_json_text(root)

        data = json.loads(text)
        assert data["root_source_id"] == "src-test"

    def test_parse_to_json_text_respects_indent(self, tmp_path: Path) -> None:
        root = tmp_path / "test.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        compact = parser.parse_to_json_text(root, indent=0)
        spaced = parser.parse_to_json_text(root, indent=2)

        as_compact = json.loads(compact)
        as_spaced = json.loads(spaced)
        # Full JSON differs (e.g. recorded parser_options.indent, timestamps).
        assert as_compact["root_source_id"] == as_spaced["root_source_id"]
        assert as_compact["schema_version"] == as_spaced["schema_version"]
        assert len(compact) < len(spaced)

    def test_parse_to_json_file(self, tmp_path: Path) -> None:
        root = tmp_path / "test.dwg"
        root.write_bytes(b"\x00")
        out = tmp_path / "out" / "test.dwg.json"

        parser = Dwg2JsonParser(backend=FakeBackend())
        output_path = parser.parse_to_json_file(root, out)

        assert Path(output_path).exists()
        data = json.loads(Path(output_path).read_text())
        assert data["root_source_id"] == "src-test"

    def test_parse_to_json_file_default_location(self, tmp_path: Path) -> None:
        root = tmp_path / "test.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        output_path = parser.parse_to_json_file(root)

        assert Path(output_path).exists()
        assert Path(output_path).name == "test.dwg.json"


class TestMissingXrefPolicy:
    def test_record_policy(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={"root": [{"path": "missing.dwg"}]})
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions(missing_xref_policy="record"))

        assert result.document.completeness.status == "partial"

    def test_error_policy(self, tmp_path: Path) -> None:
        import pytest

        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        backend = FakeBackend(xref_map={"root": [{"path": "missing.dwg"}]})
        parser = Dwg2JsonParser(backend=backend)

        with pytest.raises(FileNotFoundError):
            parser.parse(root, ParseOptions(missing_xref_policy="error"))
