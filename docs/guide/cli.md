# CLI Usage

The `dwg2json` command is installed as a console script when you install the package.

```bash
dwg2json --help
```

## Commands

### `parse`

Parse a root DWG and emit one canonical JSON file.

```bash
dwg2json parse <path> [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--out`, `-o` | Same as input dir | Output directory for the JSON file |
| `--resolve-xrefs` / `--no-resolve-xrefs` | `True` | Resolve xref dependencies |
| `--bind-xrefs` / `--no-bind-xrefs` | `True` | Build composition contexts |
| `--max-xref-depth` | `8` | Recursion depth limit for nested xrefs |
| `--backend`, `-b` | `auto` | Backend to use (`auto`, `libredwg`, `null`) |
| `--indent` | `2` | JSON indentation level |
| `--missing-xref-policy` | `record` | `record` or `error` |
| `--search-root` | — | Additional xref search directory (repeatable) |
| `--emit-viewport-records` / `--no-emit-viewport-records` | `True` | Populate `Layout.viewports` |
| `--emit-layer-plot-flags` / `--no-emit-layer-plot-flags` | `True` | Layer `is_plottable` / entity `non_plot_candidate` |
| `--emit-vp-layer-overrides` / `--no-emit-vp-layer-overrides` | `True` | Per-viewport `frozen_layer_names` |
| `--emit-publication-index` / `--no-emit-publication-index` | `True` | `SourceDocument.publication_index` |
| `--emit-layout-compositions` / `--no-emit-layout-compositions` | `True` | Extra `Composition` rows (`layout_sheet`) |

**Examples:**

```bash
# Full parse with defaults
dwg2json parse ./drawing.dwg --out ./out

# Use null backend for testing
dwg2json parse ./drawing.dwg --backend null --out ./out

# Additional xref search paths
dwg2json parse ./drawing.dwg \
  --search-root /project/xrefs \
  --search-root /shared/backgrounds \
  --out ./out

# Skip xref resolution for a quick scan
dwg2json parse ./drawing.dwg --no-resolve-xrefs --no-bind-xrefs --out ./out
```

Output file naming: `<output_dir>/<original_filename>.json` — for example, `plan.dwg` becomes `plan.dwg.json`.

### `info`

Show a quick summary of a DWG without running the full xref/composition pipeline.

```bash
dwg2json info <path> [--backend auto]
```

**Example output:**

```
{
  'path': './drawing.dwg',
  'exists': True,
  'parsed': True,
  'parse_status': 'parsed',
  'backend': 'libredwg',
  'layers': 12,
  'layouts': 3,
  'blocks': 45,
  'entities': 1847,
  'raw_xrefs': 2,
  'warnings': 1
}
```

### `schema`

Print the JSON Schema for the canonical output format.

```bash
dwg2json schema > dwg2json.schema.json
```

The schema is generated from the Pydantic `DwgJsonDocument` model and can be used by any JSON Schema validator.

### `validate`

Validate an existing `.dwg.json` file against the canonical schema.

```bash
dwg2json validate ./out/drawing.dwg.json
```

Exits `0` if valid, `1` with error details if invalid.
