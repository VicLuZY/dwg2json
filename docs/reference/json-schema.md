# JSON Schema

The canonical output format is defined by the `DwgJsonDocument` Pydantic model. A JSON Schema is generated from this model and can be used for validation by any standard JSON Schema tool.

## Generating the schema

### CLI

```bash
dwg2json schema > dwg2json.schema.json
```

### Python

```python
from dwg2json.schema import generate_schema, write_schema_file

# As a dict
schema = generate_schema()

# Write to file
path = write_schema_file("dwg2json.schema.json")
```

## Validating output files

### CLI

```bash
dwg2json validate ./out/drawing.dwg.json
# Exit 0 = valid, Exit 1 = invalid with error details
```

### Python

```python
from dwg2json.schema import validate_json_file, validate_document

# Validate a file on disk
errors = validate_json_file("drawing.dwg.json")
if errors:
    for e in errors:
        print(e)

# Validate a dict
import json
data = json.loads(Path("drawing.dwg.json").read_text())
errors = validate_document(data)
```

## Model hierarchy

```
DwgJsonDocument
├── ParserInfo
├── SourceDocument[]
│   ├── Layer[]
│   ├── Layout[]
│   ├── BlockDefinition[]
│   ├── Entity[]
│   │   ├── Point3D (insert_point, scale)
│   │   ├── BoundingBox (bbox)
│   │   └── WarningRecord[]
│   ├── XrefBindingMetadata
│   └── WarningRecord[]
├── XrefGraph
│   ├── XrefGraphNode[]
│   └── XrefGraphEdge[]
├── Composition[]
│   └── SourceBinding[]
├── CompletenessReport
├── InterpretationConfidence
│   └── ConfidenceFactor[]
├── MissingReference[]
└── WarningRecord[]
```

## Required top-level fields

All fields in `DwgJsonDocument` have defaults and are present in every output:

| Field | Type | Default |
|-------|------|---------|
| `schema_version` | `string` | `"0.1.0"` |
| `parser` | `ParserInfo` | *(required)* |
| `root_source_id` | `string` | *(required)* |
| `sources` | `SourceDocument[]` | `[]` |
| `xref_graph` | `XrefGraph` | `{ nodes: [], edges: [] }` |
| `compositions` | `Composition[]` | `[]` |
| `completeness` | `CompletenessReport` | `{ status: "complete", ... }` |
| `interpretation_confidence` | `InterpretationConfidence` | `{ value: 1.0, ... }` |
| `interpretation_status` | `string` | `"complete"` |
| `missing_references` | `MissingReference[]` | `[]` |
| `warnings` | `WarningRecord[]` | `[]` |
| `metadata` | `object` | `{}` |

## Pre-generated schema

A pre-generated schema file ships with the package at:

```
src/dwg2json/schema/dwg2json_v0.1.0.schema.json
```
