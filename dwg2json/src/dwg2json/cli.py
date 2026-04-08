from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from .api import Dwg2JsonParser
from .models import ParseOptions

app = typer.Typer(add_completion=False, help="DWG to canonical JSON CLI")


@app.command()
def parse(
    path: Path,
    out: Path | None = typer.Option(None, "--out", help="Output directory for the canonical JSON file"),
    resolve_xrefs: bool = typer.Option(True, "--resolve-xrefs/--no-resolve-xrefs"),
    bind_xrefs: bool = typer.Option(True, "--bind-xrefs/--no-bind-xrefs"),
    max_xref_depth: int = typer.Option(8, min=0),
) -> None:
    parser = Dwg2JsonParser()
    result = parser.parse(
        path,
        ParseOptions(
            resolve_xrefs=resolve_xrefs,
            bind_xrefs=bind_xrefs,
            max_xref_depth=max_xref_depth,
            out_dir=str(out) if out else None,
        ),
    )
    print({
        "path": result.document.root_source.path,
        "backend": result.document.parser.backend,
        "sources": len(result.document.sources),
        "compositions": len(result.document.compositions),
        "warnings": len(result.document.warnings),
        "completeness": result.document.completeness.model_dump(),
        "output_json_path": result.output_json_path,
    })
