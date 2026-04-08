# Output Format

Every successful parse produces one UTF-8 JSON file aligned with the `DwgJsonDocument` schema.

## Top-level structure

```json
{
  "schema_version": "0.1.0",
  "parser": { ... },
  "root_source_id": "src-drawing",
  "sources": [ ... ],
  "xref_graph": { "nodes": [...], "edges": [...] },
  "compositions": [ ... ],
  "completeness": { ... },
  "interpretation_confidence": { ... },
  "interpretation_status": "complete",
  "missing_references": [ ... ],
  "warnings": [ ... ],
  "metadata": { ... }
}
```

## Field reference

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | `string` | Version of the canonical schema (e.g. `"0.1.0"`). |
| `parser` | `ParserInfo` | Parser name, version, backend, backend version, UTC timestamp. |
| `root_source_id` | `string` | ID of the root `SourceDocument`. |
| `sources` | `SourceDocument[]` | One record per root or xref source file. |
| `xref_graph` | `XrefGraph` | Dependency graph with nodes and edges. |
| `compositions` | `Composition[]` | Composed spatial contexts binding sources together. |
| `completeness` | `CompletenessReport` | Aggregate status, counts, and consumer caution. |
| `interpretation_confidence` | `InterpretationConfidence` | Scalar value, contributing factors, explanation. |
| `interpretation_status` | `string` | `"complete"`, `"partial"`, `"degraded"`, or `"failed"`. |
| `missing_references` | `MissingReference[]` | Structured records for missing xrefs. |
| `warnings` | `WarningRecord[]` | Cross-cutting warnings with codes and severity. |
| `metadata` | `object` | Additional data (e.g. serialized parser options). |

## SourceDocument

Each source contains the per-file truth:

```json
{
  "id": "src-drawing",
  "path": "drawing.dwg",
  "resolved_path": "/project/drawing.dwg",
  "role": "root",
  "exists": true,
  "parsed": true,
  "parse_status": "parsed",
  "parent_source_id": null,
  "xref_binding": null,
  "layers": [ ... ],
  "layouts": [ ... ],
  "blocks": [ ... ],
  "entities": [ ... ],
  "warnings": [ ... ]
}
```

For xref children, `role` is `"xref"` and `xref_binding` contains the saved path, resolved path, mode, transform, and resolution status.

## Entity

Entities use a universal shape with type-specific geometry in the `geometry` dict:

```json
{
  "id": "src-drawing__ent_1A",
  "source_id": "src-drawing",
  "handle": "1A",
  "owner_handle": "2",
  "type": "LINE",
  "layer": "WALLS",
  "layout": "Model",
  "geometry": {
    "start": [0.0, 0.0, 0.0],
    "end": [10.0, 10.0, 0.0]
  },
  "attributes": {},
  "xdata": {},
  "raw": { "handle": "1A", "layer": "WALLS" },
  "warnings": []
}
```

Supported entity types include LINE, CIRCLE, ARC, ELLIPSE, TEXT, MTEXT, INSERT, DIMENSION, HATCH, LEADER, SPLINE, LWPOLYLINE, IMAGE, 3DSOLID, and many more. Unknown types are still extracted with a best-effort generic mapping and an `unsupported-entity-type` warning.

## XrefGraph

```json
{
  "nodes": [
    { "source_id": "src-host", "path": "host.dwg", "depth": 0, "exists": true, "parsed": true }
  ],
  "edges": [
    {
      "host_source_id": "src-host",
      "target_source_id": "src-host__xref_0_bg",
      "saved_path": "bg.dwg",
      "resolved_path": "/project/bg.dwg",
      "mode": "attach",
      "transform": [[1,0,100],[0,1,200],[0,0,1]],
      "exists": true,
      "parsed": true,
      "composition_required": true
    }
  ]
}
```

## Determinism

Canonical output is sorted for stable diffs:

- Sources: root first, then by resolved path, then ID
- Entities: by handle, then ID
- Xref nodes: by depth, then source ID
- Xref edges: by host source ID, then saved path
- JSON keys: alphabetically sorted via `orjson OPT_SORT_KEYS`
