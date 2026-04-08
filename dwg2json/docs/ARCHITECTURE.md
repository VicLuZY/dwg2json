# dwg2json architecture

This document describes the design of **dwg2json**: how a single root DWG becomes one canonical JSON artifact, how truth is layered, and how xrefs, completeness, confidence, and export behavior fit together.

## Design center

The product contract is intentional and narrow:

- **One root DWG in** — A single designated drawing is the parse root; all other inputs enter only as dependencies of that root.
- **One canonical JSON out** — Exactly one serialized `DwgJsonDocument` per successful invocation (including degraded parses). No secondary “sidecar” formats are required for core semantics.

Everything else—backends, heuristics, CLI—is in service of that contract.

## Two-layer truth model

The JSON deliberately encodes two complementary views of the same drawing set.

### Source truth

Each physical or logical source (root DWG or resolved xref) is a **`SourceDocument`**:

- Own **layers**, **layouts**, **blocks**, and **entities** in native canonical form.
- **Parse lifecycle**: `exists`, `parsed`, `parse_status` (`parsed`, `partial`, `unresolved`, `missing`, `failed`).
- **Xref binding metadata** on xref children: saved path, resolved path, mode (attach/overlay/unknown), transforms, missing reasons, candidate paths.
- **Warnings** and optional **raw_summary** / metadata (e.g. `raw_xrefs` discovered before resolution).

Source truth answers: *What did we read from each file, and in what state?*

### Composition truth

**`Composition`** records describe how multiple sources are intended to be read **together** in one coordinate frame:

- **`source_bindings`**: which `source_id` participates, parent chain, placement and inherited transforms, xref mode, which entity ids are included, and whether a binding has a **missing dependency**.
- **`entity_refs`** / **`relation_refs`**: hooks for composed indexing without duplicating full geometry in every composition.
- **`completeness_status`**: `complete`, `partial`, or `missing_dependencies` at the composition level.

Composition truth answers: *How should a consumer interpret the root plus its xrefs as a single scene?*

These layers are both **first-class**. Downstream tools should use source truth for per-file analytics and composition truth for spatially coupled semantics (overlays on backgrounds, multi-file assemblies).

## Authoring vs publication (model space and layouts)

DWG usage in practice often **does not** match the textbook “everything in Model, sheets in Layout” story. dwg2json therefore carries **two complementary truths** in addition to xref composition:

1. **Authoring truth** — Every entity parsed from each layout tab remains in `sources[].entities`, tagged with **`layout`** (layout name) and optional **`space_class`** (`"model"` vs `"paper"`). Layer **`is_plottable`** (DXF plot flag) and **`Entity.non_plot_candidate`** help flag content that may not print.
2. **Publication truth** — Each **`Layout`** carries optional **`plot_settings`** (DXF **AcDbPlotSettings**: paper size, plot style sheet name, margins, plot type, standard scale enum, etc.). Non-model layouts list **`viewports`** (`ViewportRecord`: paper bounds, model view center/height, **`model_to_paper_scale`**, zoom-lock and non-rectangular clip flags, UCS fields, clipping handle, per-viewport **`frozen_layer_names`** when available). **`paper_space_entity_ids`** indexes native sheet geometry. **`interpretation_notes`** call out common mismatches (e.g. busy model space vs a single viewport). Each **`SourceDocument.metadata.backend_capabilities`** records what the backend did not expand (e.g. per-viewport layer **color/linetype** overrides in OBJECTS). **`SourceDocument.geodata`** summarises **GEODATA** when present (GIS / site coordinates, CRS XML excerpt, EPSG hints). **`metadata.spatial_sidecar_hints`** notes common **`.prj` / `.wld`** siblings. **`publication_index`** on each **`SourceDocument`** is a small navigation list for consumers and LLMs.

**`Composition.kind`** distinguishes the xref scene (`xref_scene`, default) from optional per-sheet bundles (`layout_sheet`) whose **`entity_refs`** are paper-space entities on that layout only—not the full model hoard.

**`ParseOptions`** flags (`emit_viewport_records`, `emit_layer_plot_flags`, `emit_vp_layer_overrides`, `emit_publication_index`, `emit_layout_compositions`) default to **on**; turn them off for stricter backward compatibility or smaller JSON.

The LibreDWG backend can read **`.dxf`** files directly with **ezdxf** (no `dwg2dxf` required), which is useful for tests and text-based fixtures.

## Why xref binding is first-class

In CAD workflows, meaning is often **not local** to a single file:

- An **overlay** may contain equipment or annotations that only make sense on top of a **background** xref.
- **Spatial alignment** depends on xref insertion points, scales, rotations, and attach vs overlay behavior.
- **Missing** xrefs are common in the wild; silently ignoring them produces false confidence.

Therefore dwg2json does **not** treat xrefs as optional attachments. They are **composition dependencies**:

- The **`xref_graph`** records the dependency structure (nodes = sources, edges = host → target with paths and flags).
- **Resolution** walks the graph with depth limits, cycle detection, and configurable search roots.
- **Binding** materializes how each resolved child participates in composed contexts.

If xref handling were only “extra metadata,” consumers would have to re-derive composition rules and would routinely mis-handle partial data.

## Pipeline stages

End-to-end flow (as orchestrated by `Dwg2JsonParser.parse`):

1. **Backend parse** — Selected `DwgBackend` reads the root path and returns a `ParseResult` with an initial `DwgJsonDocument` (root `SourceDocument`, initial `xref_graph` node, warnings).
2. **Xref resolution** (optional, `resolve_xrefs=True`) — `XrefResolver` reads `raw_xrefs` (and related metadata), resolves paths, parses child drawings through the same backend, merges sources and graph edges, and records **`MissingReference`** entries and warnings for failures, cycles, and depth limits.
3. **Publication enrichment** — `enrich_source_publication` fills per-layout paper-space indexes, **`interpretation_notes`**, and **`publication_index`** on each **`SourceDocument`** (honouring `ParseOptions` flags).
4. **Composition** (optional, `bind_xrefs=True`) — `CompositionBuilder` constructs the xref **`Composition`** (`kind="xref_scene"`) and optional per-layout **`Composition`** rows (`kind="layout_sheet"`) for paper-space entity refs.
5. **Confidence** — `compute_confidence` applies a **monotonic** heuristic to `interpretation_confidence` based on missing/failed/unresolved xrefs, unsupported entities, and generic backend warnings.
6. **Completeness, status, and export** — `CompletenessReport.recompute_from_document` aggregates xref-related problems; `derive_interpretation_status` combines completeness with confidence into `interpretation_status`; parser options are stored in `metadata`; if `out_dir` is set, `export_json_file` writes sorted JSON.

Stages 2–4 and publication flags can be adjusted via `ParseOptions` for faster introspection or debugging, at the cost of incomplete graph, layout, or publication data.

## Backend adapter boundary

Backends implement **`DwgBackend`**: given a **`Path`** and **`ParseOptions`**, they return **`ParseResult`**.

**Responsibilities of a backend**

- Determine availability (e.g. whether `dwg2dxf` exists, optionally via `DWG2JSON_DWG2DXF`). **`.dxf`** inputs are read with **ezdxf** only and do not require `dwg2dxf`.
- Perform format-specific decoding (DWG → internal representation). The LibreDWG adapter writes a transient DXF under `tempfile.TemporaryDirectory` and deletes it after `ezdxf` loads the file.
- Populate at least one **`SourceDocument`** for the root and seed **`xref_graph.nodes`** for the root.
- Stash xref discovery results where the resolver expects them (e.g. `metadata["raw_xrefs"]` as a list of path/mode/transform hints).

**Out of scope for backends**

- Recursive xref expansion (handled by **`XrefResolver`**).
- Composition binding (handled by **`CompositionBuilder`**).
- Global confidence and completeness recomputation (handled after composition).

This boundary keeps native decoders replaceable (Python, future Rust/C bindings, etc.) while the rest of the pipeline stays stable.

## Canonical JSON schema overview

The on-wire format is the JSON serialization of **`DwgJsonDocument`**, validated in development via Pydantic v2 and exposed as JSON Schema through **`dwg2json schema`**.

Major aggregates:

- **Document** — `schema_version`, `parser`, `root_source_id`, top-level `metadata`.
- **Sources** — Ordered list of **`SourceDocument`** (root and xrefs).
- **Graph** — **`XrefGraph`** with **`XrefGraphNode`** and **`XrefGraphEdge`**.
- **Compositions** — List of **`Composition`**.
- **Quality** — **`CompletenessReport`**, **`InterpretationConfidence`**, `interpretation_status`, **`missing_references`**, **`warnings`**.

**Entities** use a universal **`Entity`** shape: stable **`id`**, **`source_id`**, **`handle`**, **`type`**, styling, optional block insert fields, **`geometry`** dict, transforms, and optional **`raw`** for provenance.

## Missing dependency model

Missing or broken xrefs are **normal**; the schema is designed to make them **visible**:

| Signal | Meaning |
|--------|---------|
| `SourceDocument.parse_status` | Per-source outcome (`missing`, `unresolved`, `failed`, …). |
| `XrefGraphEdge.exists` / `parsed` | Whether the edge’s target was located and successfully parsed. |
| `missing_references` | Structured list with paths, parent document, severity, and interpretation impact. |
| `Composition.missing_source_ids` / `completeness_status` | Composed view knows which dependencies failed. |
| `CompletenessReport` | Rollup counts and `consumer_caution` text. |

`ParseOptions.missing_xref_policy` controls whether missing xrefs are **recorded** (default) or cause a hard **error** where the pipeline supports it—without breaking the “one JSON” contract for the `record` path.

## Confidence heuristics

**`InterpretationConfidence`** is a deliberate **heuristic**, not a statistical model:

- **Monotonic penalties** — Each issue adds penalties; the final **`value`** is derived so it only decreases when new problems appear (clamped to `[0, 1]`).
- **Factor ledger** — Every applied penalty is recorded in **`factors`** with a short **`detail`** for debugging and UI.
- **Typical inputs** — Missing xrefs, failed xref parses, cycle-blocked references, unsupported entity types (from warnings), and capped aggregate backend warnings.

**`interpretation_status`** (`complete`, `partial`, `degraded`, `failed`) combines **`completeness.status`** with the confidence scalar so a single field can drive UX thresholds.

Consumers should treat **`interpretation_confidence.value`** as a **relative** signal for ranking or gating automation, not as a calibrated probability.

## Determinism rules

Canonical output aims to be **stable** across runs for the same inputs and options:

- **Document sorting** (`export_json` / `to_json_text`) — Sources: root first, then by `resolved_path`, then `id`. Entities: by `handle`, then `id`. Layers/blocks: by name. Xref nodes: by `depth`, then `source_id`. Edges: by `host_source_id`, then `saved_path`. Compositions: by `id`. Warnings and missing references: by stable tuple keys.
- **JSON serialization** — **orjson** with **`OPT_SORT_KEYS`** so object key order is repeatable; optional indent for readability.
- **Stable ids** — Backend helpers generate predictable ids (e.g. `{root_id}__ent_{handle}`) so the same drawing yields the same entity ids across runs.

Floating-point noise from converters can still differ slightly between platforms; the sorting and key ordering rules target **structural** determinism.

## Schema versioning strategy

- **`schema_version`** on the document (e.g. `0.2.0`) is the **compatibility anchor** for consumers.
- **JSON Schema** is generated from the Pydantic models (`DwgJsonDocument.model_json_schema`); it tracks the same logical version.
- **Breaking changes** (field removals, type changes, renamed required fields) should bump **`schema_version`** according to project policy (semver-like for the schema string) and be documented in release notes.
- **Non-breaking additions** (optional fields, new optional array elements) may keep the minor component stable or follow a documented additive policy.

Tools should **read `schema_version` first**, then apply version-specific logic if they support multiple generations of the format.

---

For day-to-day usage, see the [README](../README.md). For implementation details, follow the modules under `src/dwg2json/` (`api.py`, `backends/`, `pipeline/`).
