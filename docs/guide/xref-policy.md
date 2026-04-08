# Xref Policy

External references in DWG files are not treated as isolated drawings. They are **composition dependencies** — content that must be interpreted together with the host drawing in a shared coordinate frame.

## Why this matters

In real CAD practice:

- A **device layout** overlaid on a **floor plan** xref only makes sense when both are placed together. Parsing the overlay alone is semantically weak.
- **Spatial alignment** depends on insertion points, scales, rotations, and attach vs. overlay mode.
- **Missing xrefs** are common in archived project folders. Silently ignoring them produces false confidence.

## Three layers of truth

dwg2json records xref relationships at three levels:

### 1. Source truth

Each file (root or xref) is preserved as its own `SourceDocument` with local entities, layers, blocks, and xref declarations. Source truth answers: *What did we read from each file?*

### 2. Graph truth

The `xref_graph` encodes who depends on whom. Each edge records the saved path, resolved path, transform, and whether the target was found and parsed. Graph truth answers: *What is the dependency structure?*

### 3. Composition truth

`Composition` objects describe how sources are bound together for interpretation. Source bindings carry placement transforms and inherited transform chains. Composition truth answers: *How should a consumer interpret the combined scene?*

## Missing xref behavior

When an xref target cannot be found:

| Signal | Value |
|--------|-------|
| `SourceDocument.exists` | `false` |
| `SourceDocument.parse_status` | `"missing"` |
| `XrefGraphEdge.exists` | `false` |
| `Composition.missing_source_ids` | Contains the missing source ID |
| `Composition.completeness_status` | `"missing_dependencies"` |
| `CompletenessReport.status` | `"partial"` |
| `CompletenessReport.consumer_caution` | Explanation string |
| `missing_references` | Structured record with path, severity, impact |
| `interpretation_confidence.value` | Reduced by penalty |

The xref graph edge is **always preserved** even when the target is missing. Consumers can see exactly which dependencies were declared and which were unresolvable.

## Missing xref policy

Controlled by `ParseOptions.missing_xref_policy`:

- **`"record"`** (default) — Record the missing dependency and continue. The output JSON is always produced, with degraded completeness.
- **`"error"`** — Raise a `FileNotFoundError` on the first missing xref. Useful for CI pipelines that require fully resolved inputs.

## Cycle detection

If xref A references B which references A (directly or transitively), the resolver:

1. Detects the cycle
2. Stops recursion safely
3. Records the cycle-blocked source with `parse_status="unresolved"`
4. Emits an `xref-cycle` warning
5. Reduces confidence

## Search order

Xref paths are resolved in priority order:

1. Absolute path (if the saved path is absolute)
2. Relative to the host DWG's directory
3. Filename-only in the host directory
4. Each configured `xref_search_roots` directory
