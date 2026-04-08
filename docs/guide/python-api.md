# Python API

The public API is centered on `Dwg2JsonParser`. Import it from the top-level package:

```python
from dwg2json import Dwg2JsonParser, ParseOptions
```

## Dwg2JsonParser

### Constructor

```python
parser = Dwg2JsonParser(backend=None)
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `backend` | `DwgBackend \| str \| None` | `None` | Backend instance, name string (`"auto"`, `"libredwg"`, `"null"`), or `None` for auto-detection. |

### Core method: `parse`

```python
result = parser.parse(path, options=None)
```

Returns a `ParseResult` containing the canonical `DwgJsonDocument`.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | `Path` | — | Path to the root DWG file. |
| `options` | `ParseOptions \| None` | `None` | Parse configuration. Defaults to `ParseOptions()`. |

### Convenience methods

```python
# Returns DwgJsonDocument directly
doc = parser.parse_file("drawing.dwg")

# Returns canonical JSON as a string
json_text = parser.parse_to_json_text("drawing.dwg", indent=2)

# Writes JSON file, returns the output path as a string
output_path = parser.parse_to_json_file("drawing.dwg", "output.dwg.json")
```

## ParseOptions

All fields are optional with sensible defaults.

```python
options = ParseOptions(
    resolve_xrefs=True,          # Resolve xref dependencies
    bind_xrefs=True,             # Build composition contexts
    max_xref_depth=8,            # Recursion limit for nested xrefs
    missing_xref_policy="record",# "record" or "error"
    xref_search_roots=[],        # Additional directories to search for xrefs
    out_dir=None,                # Output directory (None = don't auto-write)
    backend="auto",              # Backend name
    keep_raw_payloads=True,      # Include raw DXF data in entities
    indent=2,                    # JSON indentation
)
```

## ParseResult

```python
result = parser.parse(path, options)

result.document            # DwgJsonDocument
result.output_json_path    # str | None — path if JSON was written
result.source_path         # Path — root source path

# Write JSON file on demand
path = result.write_json_file(output_dir="./out")

# Get JSON as string
text = result.to_json_text(indent=2)
```

## DwgJsonDocument

The canonical document model. Key properties and fields:

```python
doc = result.document

doc.schema_version             # "0.2.0"
doc.parser                     # ParserInfo (name, version, backend, timestamp)
doc.root_source_id             # ID of the root SourceDocument
doc.sources                    # list[SourceDocument]
doc.xref_graph                 # XrefGraph (nodes + edges)
doc.compositions               # list[Composition]
doc.completeness               # CompletenessReport
doc.interpretation_confidence  # InterpretationConfidence
doc.interpretation_status      # "complete" | "partial" | "degraded" | "failed"
doc.missing_references         # list[MissingReference]
doc.warnings                   # list[WarningRecord]
doc.metadata                   # dict

# Convenience properties
doc.root_source                # SourceDocument for the root
doc.all_entities               # Flattened list across all sources
doc.all_layers                 # Flattened list across all sources
```

## Error handling

With `missing_xref_policy="record"` (default), missing xrefs produce warnings and degrade completeness but do not raise exceptions.

With `missing_xref_policy="error"`, a `FileNotFoundError` is raised on the first missing xref:

```python
from dwg2json import Dwg2JsonParser, ParseOptions

parser = Dwg2JsonParser()
try:
    result = parser.parse(path, ParseOptions(missing_xref_policy="error"))
except FileNotFoundError as e:
    print(f"Missing dependency: {e}")
```
