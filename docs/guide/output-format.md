# Output Format

Every successful parse produces one UTF-8 JSON file aligned with the `DwgJsonDocument` schema.

## Top-level structure

```json
{
  "schema_version": "0.2.0",
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
| `schema_version` | `string` | Version of the canonical schema (e.g. `"0.2.0"`). |
| `parser` | `ParserInfo` | Parser name, version, backend, backend version, UTC timestamp. |
| `root_source_id` | `string` | ID of the root `SourceDocument`. |
| `sources` | `SourceDocument[]` | One record per root or xref source file. |
| `xref_graph` | `XrefGraph` | Dependency graph with nodes and edges. |
| `compositions` | `Composition[]` | Composed contexts: xref scene (`kind: "xref_scene"`) and optional per-sheet paper-space bundles (`kind: "layout_sheet"`). |
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
  "warnings": [ ... ],
  "publication_index": [ ... ]
}
```

For xref children, `role` is `"xref"` and `xref_binding` contains the saved path, resolved path, mode, transform, and resolution status.

### Authoring vs publication

- **`Entity.space_class`** — `"model"` when `layout` is Model, otherwise `"paper"` for entities emitted from a paper-space layout tab.
- **`Entity.non_plot_candidate`** — When layer plot flags are emitted, `true` if the entity’s layer is marked non-plottable in DXF.
- **`Layer.is_plottable`** — DXF layer plot flag when available (default treated as plottable when unspecified).
- **`Layout.plot_settings`** — Optional dict of **AcDbPlotSettings** fields from the LAYOUT object (paper size string, `current_style_sheet` CTB/STB name, margins, `plot_type`, `standard_scale_type`, numeric paper width/height in mm, etc.).
- **`Layout.viewports`** — `ViewportRecord` entries (paper size, model view, `model_to_paper_scale` from ezdxf, `viewport_zoom_locked`, `non_rectangular_clipping`, UCS, frozen layer names when present).
- **`Layout.paper_space_entity_ids`** — Handles (canonical entity `id` values) for paper-native geometry on that layout.
- **`SourceDocument.publication_index`** — Compact `{ layout_name, viewport_record_id, role, notes }` entries for navigation.
- **`SourceDocument.geodata`** — When the drawing has model-space **GEODATA** (AutoCAD / Map 3D style geolocation), a **`GeodataSummary`** is emitted: coordinate type, design/reference points, unit scales, optional CRS XML (truncated if huge), **`epsg_code_hints`** heuristically parsed from XML, and mesh counts. **`metadata.insunits`** holds the raw `$INSUNITS` integer; **`metadata.units`** remains the human-readable unit name.
- **`metadata.spatial_sidecar_hints`** — Whether **`basename.prj`**, **`.wld3`**, or **`.wld`** exist beside the drawing (common for GIS workflows; Esri often expects a sidecar `.prj`).

Disable enrichment via `ParseOptions` (e.g. `emit_viewport_records`, `emit_layer_plot_flags`, `emit_vp_layer_overrides`, `emit_publication_index`, `emit_layout_compositions`, `emit_layout_plot_settings`, `emit_geodata`, `emit_spatial_sidecar_hints`, `emit_field_literal_warnings`).

**Warnings** may include `missing-paperspace-viewport-id-1`, `viewport-clip-unresolved`, `layer-vp-property-overrides-not-exported`, and `mtext-field-literals` (MTEXT with `%<` cached field syntax). Check **`sources[].metadata.backend_capabilities`** for `layer_viewport_property_overrides` and **`geodata`** (`exported` | `absent`).

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
  "space_class": "model",
  "non_plot_candidate": null,
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
