# Configuration

All configuration is passed via `ParseOptions` (Python) or CLI flags. There are no config files.

## ParseOptions reference

| Field | Type | Default | CLI Flag | Description |
|-------|------|---------|----------|-------------|
| `resolve_xrefs` | `bool` | `True` | `--resolve-xrefs` / `--no-resolve-xrefs` | Whether to resolve xref dependencies |
| `bind_xrefs` | `bool` | `True` | `--bind-xrefs` / `--no-bind-xrefs` | Whether to build composition contexts |
| `max_xref_depth` | `int` | `8` | `--max-xref-depth` | Maximum recursion depth for nested xrefs |
| `missing_xref_policy` | `"record"` \| `"error"` | `"record"` | `--missing-xref-policy` | How to handle missing xref targets |
| `xref_search_roots` | `list[str]` | `[]` | `--search-root` (repeatable) | Additional directories to search for xref files |
| `out_dir` | `str \| None` | `None` | `--out`, `-o` | Output directory for the canonical JSON |
| `backend` | `str` | `"auto"` | `--backend`, `-b` | Backend name: `auto`, `libredwg`, `null` |
| `keep_raw_payloads` | `bool` | `True` | — | Include raw DXF data in entity `raw` field |
| `indent` | `int` | `2` | `--indent` | JSON indentation level |

## Environment variables

| Variable | Applies to | Description |
|----------|------------|-------------|
| `DWG2JSON_DWG2DXF` | **libredwg** backend | Absolute path to the `dwg2dxf` executable. If unset or invalid, the backend falls back to `dwg2dxf` on `PATH`. |

## Xref search roots

When a saved xref path cannot be resolved relative to the host DWG, search roots provide fallback locations:

```python
options = ParseOptions(
    xref_search_roots=[
        "/project/shared-xrefs",
        "/archive/backgrounds",
    ],
)
```

```bash
dwg2json parse drawing.dwg \
  --search-root /project/shared-xrefs \
  --search-root /archive/backgrounds \
  --out ./out
```

Search order for each xref:
1. Absolute path (if saved path is absolute)
2. Relative to host DWG directory
3. Filename-only in host directory
4. Each search root (both full relative path and filename-only)

## Max xref depth

Prevents infinite recursion in deeply nested or cyclic xref chains. Set to `0` to skip xref parsing entirely (only the root is processed).

```python
# Process up to 3 levels of nesting
options = ParseOptions(max_xref_depth=3)
```

## Missing xref policy

| Policy | Behavior |
|--------|----------|
| `"record"` | Missing xrefs are recorded in the output with degraded completeness. The parse always completes. |
| `"error"` | A `FileNotFoundError` is raised on the first missing xref. Useful in CI to enforce fully resolved inputs. |

## Backend selection

| Name | Description |
|------|-------------|
| `"auto"` | Try LibreDWG, fall back to null |
| `"libredwg"` | Require LibreDWG (`dwg2dxf` on PATH) |
| `"null"` | Empty-but-valid results |
