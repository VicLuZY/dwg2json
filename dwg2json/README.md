# dwg2json

Open-source DWG semantic deparser to one canonical JSON file.

[![CI](https://img.shields.io/badge/CI-placeholder-lightgrey)](https://example.com)
[![PyPI](https://img.shields.io/badge/PyPI-placeholder-lightgrey)](https://pypi.org/project/dwg2json/)
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)

## Overview

**dwg2json** is built around a single product boundary: **one root DWG in, one canonical JSON out**. The output is a structured document suitable for tooling, indexing, and downstream interpretation—not a bag of unrelated files.

External references (**xrefs**) are treated as **bound composition dependencies**, not as standalone drawings. The JSON records how the host and referenced drawings relate (paths, graph edges, placements, composed views). When an xref cannot be found or parsed, that fact is **explicitly reported** via completeness fields, missing-reference records, and confidence metadata so consumers never mistake a partial scene for a complete one.

## Features

- **Canonical JSON output** — One `DwgJsonDocument` schema per parse, with JSON Schema available via the CLI.
- **Xref composition** — Dependency graph, per-source models, and composed contexts that bind host and xref geometry in a shared interpretation frame.
- **Missing xref tracking** — Missing, unresolved, and failed dependencies surface in `completeness`, `missing_references`, xref graph nodes/edges, and warnings.
- **Confidence heuristics** — `interpretation_confidence` aggregates monotonic penalties for missing xrefs, parse failures, cycles, and similar issues.
- **Pluggable backends** — Decode behind a stable `DwgBackend` interface; swap or extend implementations without changing the public pipeline.
- **CLI and Python API** — Typer-based CLI for parse, introspection, schema dump, and validation; `Dwg2JsonParser` for programmatic use.

## Installation

```bash
pip install dwg2json
```

**Real DWG decoding** uses the **LibreDWG** toolchain: the `dwg2dxf` binary must be installed and available on your `PATH`. The library converts DWG → DXF, then reads the DXF in Python.

**DXF parsing** for that path requires **[ezdxf](https://github.com/mozman/ezdxf)**. Install it alongside the package, for example:

```bash
pip install ezdxf
```

If LibreDWG is missing, the default `auto` backend falls back to the **null** backend (structure-only, no geometry), which is useful for tests and pipeline development.

Requires **Python 3.11+**.

## Quick start

```python
from pathlib import Path

from dwg2json import Dwg2JsonParser, ParseOptions

parser = Dwg2JsonParser()  # or Dwg2JsonParser(backend="libredwg")

result = parser.parse(
    Path("example.dwg"),
    options=ParseOptions(
        resolve_xrefs=True,
        bind_xrefs=True,
        max_xref_depth=8,
        out_dir="./out",
    ),
)

# Written automatically when out_dir is set; or call explicitly:
# result.write_json_file(Path("./out"))

print(result.output_json_path)
print(result.document.completeness.status)
print(result.document.interpretation_confidence.value)
```

`ParseOptions` also supports `missing_xref_policy` (`record` | `error`), `xref_search_roots`, `backend`, `keep_raw_payloads`, and JSON `indent`.

## CLI usage

| Command | Purpose |
|--------|---------|
| `parse` | Parse a root DWG and emit one canonical JSON file. |
| `info` | Summarize a DWG (layers, layouts, blocks, entity count, raw xref count) without running the full xref/composition pipeline. |
| `schema` | Print the JSON Schema for the canonical output (`DwgJsonDocument`). |
| `validate` | Validate an existing output file (e.g. `drawing.dwg.json`) against that schema. |

Examples:

```bash
# Full parse with xref resolution and binding (defaults)
dwg2json parse ./drawing.dwg --out ./out --resolve-xrefs --bind-xrefs --max-xref-depth 8

# Choose backend explicitly
dwg2json parse ./drawing.dwg --backend libredwg --out ./out

# Extra xref search locations
dwg2json parse ./drawing.dwg --search-root /path/to/xrefs --out ./out

# Introspection only
dwg2json info ./drawing.dwg

# Schema and validation
dwg2json schema > dwg2json.schema.json
dwg2json validate ./out/drawing.dwg.json
```

Default output path: **`<output_dir>/<original_filename>.json`** (for `plan.dwg` → `plan.dwg.json`).

## Output format

The canonical file is a single JSON object aligned with **`DwgJsonDocument`**. Top-level fields include:

| Field | Role |
|-------|------|
| `schema_version` | Version of the canonical schema (e.g. `0.1.0`). |
| `parser` | Parser name, version, backend id, optional backend version, UTC timestamp. |
| `root_source_id` | Identifier of the root `SourceDocument`. |
| `sources` | One record per root or xref **source**: layers, layouts, blocks, entities, xref binding metadata, parse status, warnings. |
| `xref_graph` | **Nodes** (sources in the dependency tree) and **edges** (host → target, paths, transforms, existence/parsed flags). |
| `compositions` | Composed views: which sources are bound, placement transforms, entity refs, per-composition completeness. |
| `completeness` | Aggregate counts and status (`complete` / `partial` / `incomplete`) plus consumer-oriented notes. |
| `interpretation_confidence` | Scalar `value` in `[0, 1]`, contributing `factors`, and a short `explanation`. |
| `interpretation_status` | `complete`, `partial`, `degraded`, or `failed`, derived from completeness and confidence. |
| `missing_references` | Structured records for missing xrefs (paths, severity, impact). |
| `warnings` | Cross-cutting `WarningRecord` entries (codes, severity, optional source/handle). |
| `metadata` | Additional bag (e.g. serialized `parser_options`). |

Entities are normalized **handles**, **geometry** payloads (type-specific dicts), optional **transforms**, and provenance-friendly **raw** snippets when enabled.

Use `dwg2json schema` or the `dwg2json.schema` module for the authoritative JSON Schema.

## Xref policy

Xrefs are **composition dependencies**: an overlay only has meaning relative to its host’s coordinate frame and the resolved target drawing. The canonical JSON therefore includes:

- **Source truth** — Each file (root or xref) as its own `SourceDocument` with local entities and xref declarations.
- **Graph truth** — `xref_graph` encodes who depends on whom and whether each edge resolved.
- **Composition truth** — `compositions` describe how sources are combined for interpretation.

If an xref is **missing** or **broken**, the pipeline still emits one JSON file: graph and source entries preserve the dependency, `completeness` and `missing_references` state that interpretation is **partial** or **incomplete**, and **consumers must not** treat the result as a fully resolved scene without checking those fields.

## Architecture

Processing is organized in four conceptual layers:

1. **Layer 1 — Python API** — `Dwg2JsonParser` orchestrates parsing, options, optional file export, and convenience helpers (`parse_to_json_file`, etc.).
2. **Layer 2 — Backend adapter** — `DwgBackend` implementations ingest a path and return a `ParseResult` containing an initial `DwgJsonDocument` (at minimum the root source and xref hints such as `raw_xrefs` in metadata).
3. **Layer 3 — Normalizer** — Backend output is mapped into shared models (`SourceDocument`, `Entity`, `Layer`, …) with stable id conventions; unsupported constructs become warnings rather than silent drops where possible.
4. **Layer 4 — Xref composition** — `XrefResolver` expands dependencies; `CompositionBuilder` binds placements; completeness and confidence run before export.

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for a deeper design discussion.

## Backends

| Backend | Description |
|---------|-------------|
| **`libredwg`** | Runs **`dwg2dxf`** (LibreDWG) to produce a temporary DXF, then loads it with **ezdxf** and walks the document into canonical models. Requires `dwg2dxf` on `PATH` and `ezdxf` installed in the environment. |
| **`null`** | Returns a valid, minimal document (empty entities, stub layouts) for testing and development without a decoder. |
| **`auto`** | Uses LibreDWG when `dwg2dxf` is available; otherwise the null backend. |

Register or select backends via `get_backend(name)` and `ParseOptions.backend` / `dwg2json parse --backend`.

## Development

Clone the repository and install in editable mode with dev dependencies:

```bash
pip install -e ".[dev]"
```

- **Tests:** `pytest` (project uses `pythonpath = ["src"]` in config).
- **Lint:** `ruff check .` (and `ruff format` if you adopt formatting).

## License

This project is licensed under the **GNU Affero General Public License v3.0 or later** (AGPL-3.0-or-later).

## Third-party

Third-party package and tooling notices are summarized in **[LICENSES_THIRD_PARTY.md](LICENSES_THIRD_PARTY.md)** when shipped with the distribution.
