"""JSON Schema generation and validation for dwg2json canonical output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import DwgJsonDocument


def generate_schema() -> dict[str, Any]:
    """Return the JSON Schema derived from the Pydantic model."""
    return DwgJsonDocument.model_json_schema(mode="serialization")


def write_schema_file(output_path: Path | str | None = None) -> Path:
    """Write the JSON Schema to a file and return the path."""
    if output_path is None:
        output_path = Path(__file__).parent / "dwg2json_v0.2.0.schema.json"
    output_path = Path(output_path)
    output_path.write_text(json.dumps(generate_schema(), indent=2) + "\n", encoding="utf-8")
    return output_path


def validate_document(data: dict[str, Any]) -> list[str]:
    """Validate a dict against the canonical schema.

    Returns a list of human-readable error strings (empty = valid).
    Uses Pydantic's own validation rather than jsonschema to keep
    dependencies minimal.
    """
    errors: list[str] = []
    try:
        DwgJsonDocument.model_validate(data)
    except Exception as exc:
        errors.append(str(exc))
    return errors


def validate_json_file(path: Path | str) -> list[str]:
    """Validate a JSON file on disk."""
    path = Path(path)
    if not path.exists():
        return [f"File not found: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]
    return validate_document(data)
