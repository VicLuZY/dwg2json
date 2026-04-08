"""Tests for the CLI."""

import json
from pathlib import Path

from typer.testing import CliRunner

from dwg2json.cli import app

runner = CliRunner()


class TestParseCommand:
    def test_parse_creates_json(self, tmp_path: Path) -> None:
        root = tmp_path / "test.dwg"
        root.write_bytes(b"\x00")
        out_dir = tmp_path / "out"

        result = runner.invoke(app, [
            "parse", str(root),
            "--out", str(out_dir),
            "--backend", "null",
        ])
        assert result.exit_code == 0
        output_file = out_dir / "test.dwg.json"
        assert output_file.exists()

        data = json.loads(output_file.read_text())
        assert data["schema_version"] == "0.1.0"

    def test_parse_no_resolve(self, tmp_path: Path) -> None:
        root = tmp_path / "test.dwg"
        root.write_bytes(b"\x00")
        out_dir = tmp_path / "out"

        result = runner.invoke(app, [
            "parse", str(root),
            "--out", str(out_dir),
            "--no-resolve-xrefs",
            "--no-bind-xrefs",
            "--backend", "null",
        ])
        assert result.exit_code == 0

    def test_parse_rejects_invalid_missing_xref_policy(self, tmp_path: Path) -> None:
        root = tmp_path / "test.dwg"
        root.write_bytes(b"\x00")
        result = runner.invoke(app, [
            "parse", str(root),
            "--backend", "null",
            "--missing-xref-policy", "bogus",
        ])
        assert result.exit_code != 0
        combined = (result.stdout or "") + (result.stderr or "")
        assert "record" in combined


class TestSchemaCommand:
    def test_schema_outputs_json(self) -> None:
        result = runner.invoke(app, ["schema"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "title" in data or "properties" in data or "$defs" in data


class TestValidateCommand:
    def test_validate_valid_file(self, tmp_path: Path) -> None:
        root = tmp_path / "test.dwg"
        root.write_bytes(b"\x00")
        out_dir = tmp_path / "out"

        runner.invoke(app, [
            "parse", str(root),
            "--out", str(out_dir),
            "--backend", "null",
        ])

        result = runner.invoke(app, ["validate", str(out_dir / "test.dwg.json")])
        assert result.exit_code == 0

    def test_validate_bad_file(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text('{"not": "valid"}')

        result = runner.invoke(app, ["validate", str(bad)])
        assert result.exit_code == 1

    def test_validate_missing_file(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["validate", str(tmp_path / "nope.json")])
        assert result.exit_code == 1
