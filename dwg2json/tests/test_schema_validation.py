"""Tests for JSON Schema generation and validation."""

import json
from pathlib import Path

from dwg2json.api import Dwg2JsonParser
from dwg2json.models import ParseOptions
from dwg2json.schema import generate_schema, validate_document, validate_json_file
from tests.conftest import FakeBackend


class TestSchemaGeneration:
    def test_generates_schema(self) -> None:
        schema = generate_schema()
        assert isinstance(schema, dict)
        assert "properties" in schema or "$defs" in schema

    def test_schema_has_title(self) -> None:
        schema = generate_schema()
        assert schema.get("title") == "DwgJsonDocument"

    def test_schema_is_valid_json(self) -> None:
        schema = generate_schema()
        text = json.dumps(schema)
        parsed = json.loads(text)
        assert parsed == schema


class TestDocumentValidation:
    def test_valid_document(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions())

        data = result.document.model_dump(mode="json")
        errors = validate_document(data)
        assert errors == []

    def test_invalid_document(self) -> None:
        errors = validate_document({"bad": "data"})
        assert len(errors) > 0

    def test_empty_dict(self) -> None:
        errors = validate_document({})
        assert len(errors) > 0


class TestFileValidation:
    def test_valid_json_file(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")

        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions(out_dir=str(tmp_path / "out")))

        errors = validate_json_file(result.output_json_path)
        assert errors == []

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        errors = validate_json_file(tmp_path / "nope.json")
        assert len(errors) == 1
        assert "not found" in errors[0].lower() or "File not found" in errors[0]

    def test_invalid_json_file(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("not json at all")
        errors = validate_json_file(bad)
        assert len(errors) > 0

    def test_valid_json_but_wrong_schema(self, tmp_path: Path) -> None:
        wrong = tmp_path / "wrong.json"
        wrong.write_text('{"foo": "bar"}')
        errors = validate_json_file(wrong)
        assert len(errors) > 0
