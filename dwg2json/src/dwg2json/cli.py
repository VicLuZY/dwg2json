"""CLI for dwg2json.

Usage::

    dwg2json parse ./drawing.dwg --out ./out --resolve-xrefs --bind-xrefs
    dwg2json info ./drawing.dwg
    dwg2json schema
    dwg2json validate ./drawing.dwg.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from .api import Dwg2JsonParser
from .backends.registry import get_backend
from .models import ParseOptions

app = typer.Typer(add_completion=False, help="dwg2json — DWG to canonical JSON CLI")
console = Console()

_MISSING_XREF_POLICIES = frozenset({"record", "error"})


def _validate_missing_xref_policy(value: str) -> str:
    if value not in _MISSING_XREF_POLICIES:
        allowed = ", ".join(sorted(_MISSING_XREF_POLICIES))
        raise typer.BadParameter(f"must be one of: {allowed}")
    return value


@app.command()
def parse(
    path: Path = typer.Argument(..., help="Path to the root DWG file"),
    out: Path | None = typer.Option(None, "--out", "-o", help="Output directory"),
    resolve_xrefs: bool = typer.Option(True, "--resolve-xrefs/--no-resolve-xrefs"),
    bind_xrefs: bool = typer.Option(True, "--bind-xrefs/--no-bind-xrefs"),
    max_xref_depth: int = typer.Option(8, "--max-xref-depth", min=0),
    backend: str = typer.Option("auto", "--backend", "-b"),
    indent: int = typer.Option(2, "--indent"),
    missing_xref_policy: str = typer.Option(
        "record",
        "--missing-xref-policy",
        callback=_validate_missing_xref_policy,
    ),
    search_roots: list[str] | None = typer.Option(None, "--search-root"),
    emit_viewport_records: bool = typer.Option(
        True, "--emit-viewport-records/--no-emit-viewport-records",
    ),
    emit_layer_plot_flags: bool = typer.Option(
        True, "--emit-layer-plot-flags/--no-emit-layer-plot-flags",
    ),
    emit_vp_layer_overrides: bool = typer.Option(
        True, "--emit-vp-layer-overrides/--no-emit-vp-layer-overrides",
    ),
    emit_publication_index: bool = typer.Option(
        True, "--emit-publication-index/--no-emit-publication-index",
    ),
    emit_layout_compositions: bool = typer.Option(
        True, "--emit-layout-compositions/--no-emit-layout-compositions",
    ),
    emit_layout_plot_settings: bool = typer.Option(
        True, "--emit-layout-plot-settings/--no-emit-layout-plot-settings",
    ),
    emit_geodata: bool = typer.Option(True, "--emit-geodata/--no-emit-geodata"),
    emit_spatial_sidecar_hints: bool = typer.Option(
        True, "--emit-spatial-sidecar-hints/--no-emit-spatial-sidecar-hints",
    ),
    emit_field_literal_warnings: bool = typer.Option(
        True,
        "--emit-field-literal-warnings/--no-emit-field-literal-warnings",
    ),
) -> None:
    """Parse a DWG file and emit one canonical JSON file."""
    parser = Dwg2JsonParser(backend=backend)

    out_dir = str(out) if out else str(path.parent)
    options = ParseOptions(
        resolve_xrefs=resolve_xrefs,
        bind_xrefs=bind_xrefs,
        max_xref_depth=max_xref_depth,
        missing_xref_policy=missing_xref_policy,  # type: ignore[arg-type]  # validated by Typer
        xref_search_roots=search_roots or [],
        out_dir=out_dir,
        backend=backend,
        indent=indent,
        emit_viewport_records=emit_viewport_records,
        emit_layer_plot_flags=emit_layer_plot_flags,
        emit_vp_layer_overrides=emit_vp_layer_overrides,
        emit_publication_index=emit_publication_index,
        emit_layout_compositions=emit_layout_compositions,
        emit_layout_plot_settings=emit_layout_plot_settings,
        emit_geodata=emit_geodata,
        emit_spatial_sidecar_hints=emit_spatial_sidecar_hints,
        emit_field_literal_warnings=emit_field_literal_warnings,
    )

    result = parser.parse(path, options)

    table = Table(title="dwg2json parse result")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Source", str(result.document.root_source.path))
    table.add_row("Backend", result.document.parser.backend)
    table.add_row("Sources", str(len(result.document.sources)))
    total_entities = sum(len(s.entities) for s in result.document.sources)
    table.add_row("Entities", str(total_entities))
    table.add_row("Compositions", str(len(result.document.compositions)))
    table.add_row("Warnings", str(len(result.document.warnings)))
    table.add_row("Completeness", result.document.completeness.status)
    table.add_row("Confidence", f"{result.document.interpretation_confidence.value:.2f}")
    table.add_row("Status", result.document.interpretation_status)
    table.add_row("Output", result.output_json_path or "(not written)")
    console.print(table)


@app.command()
def info(
    path: Path = typer.Argument(..., help="Path to a DWG file"),
    backend: str = typer.Option("auto", "--backend", "-b"),
) -> None:
    """Show summary info about a DWG without full parse."""
    be = get_backend(backend)
    result = be.parse(path, ParseOptions(resolve_xrefs=False, bind_xrefs=False))
    doc = result.document
    root = doc.root_source

    rprint({
        "path": root.path,
        "exists": root.exists,
        "parsed": root.parsed,
        "parse_status": root.parse_status,
        "backend": doc.parser.backend,
        "layers": len(root.layers),
        "layouts": len(root.layouts),
        "blocks": len(root.blocks),
        "entities": len(root.entities),
        "raw_xrefs": len(root.metadata.get("raw_xrefs", [])),
        "warnings": len(root.warnings),
    })


@app.command()
def schema() -> None:
    """Print the JSON Schema for the canonical output format."""
    from .schema import generate_schema

    sys.stdout.write(json.dumps(generate_schema(), indent=2))
    sys.stdout.write("\n")


@app.command()
def validate(
    path: Path = typer.Argument(..., help="Path to a .dwg.json file to validate"),
) -> None:
    """Validate a dwg2json output file against the schema."""
    from .schema import validate_json_file

    errors = validate_json_file(path)
    if errors:
        console.print(f"[red]Validation failed with {len(errors)} error(s):[/red]")
        for err in errors:
            console.print(f"  - {err}")
        raise typer.Exit(code=1)
    console.print("[green]Valid.[/green]")
