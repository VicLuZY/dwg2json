# Schema Design

The canonical JSON schema is derived from Pydantic v2 models and versioned explicitly via `schema_version`.

## Design principles

- **Explicit names over compact names** — `interpretation_confidence` not `conf`, `missing_source_ids` not `miss_src`
- **Stable enums** — Status values, modes, and severity levels use string literals
- **Forward-compatible** — Optional fields with defaults; new fields are additive
- **Deterministic** — Sorting rules ensure stable diffs across runs
- **Provenance-preserving** — Every entity carries `source_id`, `handle`, and optional `raw` payload

## Versioning

`schema_version` (e.g. `"0.2.0"`) is the compatibility anchor:

- **Breaking changes** (removed fields, type changes, renamed required fields) bump the version
- **Non-breaking additions** (new optional fields, new array elements) may keep the version or follow a documented additive policy

Consumers should read `schema_version` first and apply version-specific logic.

## JSON Schema generation

The schema is generated at runtime from the Pydantic models:

```python
from dwg2json.schema import generate_schema
schema = generate_schema()  # returns a dict
```

```bash
dwg2json schema > dwg2json.schema.json
```

A pre-generated schema file ships at `src/dwg2json/schema/dwg2json_v0.2.0.schema.json`.

## Validation

```python
from dwg2json.schema import validate_document, validate_json_file

errors = validate_document({"bad": "data"})  # returns list[str]
errors = validate_json_file("output.dwg.json")
```

```bash
dwg2json validate output.dwg.json
```

## Determinism rules

The export pipeline applies these sorting rules before serialization:

| Collection | Sort key |
|-----------|----------|
| Sources | role (root first), then resolved_path, then id |
| Entities (per source) | handle, then id |
| Layers (per source) | name |
| Blocks (per source) | name |
| Xref graph nodes | depth, then source_id |
| Xref graph edges | host_source_id, then saved_path |
| Compositions | id |
| Warnings | severity, code, message |
| Missing references | parent_document_id, requested_path |

JSON object keys are sorted via `orjson OPT_SORT_KEYS`. Floating-point values are preserved as numbers, not strings.

## Entity model

Entities use a universal `Entity` shape rather than per-type subclasses:

```
id, source_id, handle, owner_handle, type,
layer, block_name, layout,
color_index, line_type, line_weight, is_visible,
text, insert_point, scale, rotation,
attributes, geometry, bbox, transform,
composed_transform, xdata, raw, tags, warnings
```

Type-specific data lives in the `geometry` dict. This avoids a combinatorial explosion of optional fields while keeping the schema flat and queryable.

### Example geometry payloads

**LINE:** `{ "start": [0,0,0], "end": [10,10,0] }`

**CIRCLE:** `{ "center": [5,5,0], "radius": 3.0 }`

**INSERT:** `{ "insert": [0,0,0], "block_name": "DOOR", "scale": [1,1,1], "rotation": 45.0, "transform_4x4": [[...]] }`

**HATCH:** `{ "pattern_name": "ANSI31", "solid_fill": 0, "boundary_path_count": 1 }`
