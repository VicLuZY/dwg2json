# Pipeline

The parse pipeline is orchestrated by `Dwg2JsonParser.parse()` and consists of five stages. Each stage is independently testable and can be disabled via `ParseOptions`.

## Stage 1: Backend parse

The selected `DwgBackend` reads the root DWG and returns an initial `ParseResult`:

- One `SourceDocument` for the root with layers, layouts, blocks, entities
- Initial `xref_graph` node for the root
- Raw xref declarations in `metadata["raw_xrefs"]`
- Backend-specific warnings

The backend is responsible for format-specific decoding only. It does **not** resolve xref children, build compositions, or compute confidence.

## Stage 2: Xref resolution

**Module:** `pipeline/xrefs.py`  
**Enabled by:** `resolve_xrefs=True`

The `XrefResolver` iterates over `raw_xrefs` in each source's metadata and:

1. **Resolves paths** using the priority order in `pipeline/xref_paths.py` (absolute → relative to host → filename in host dir → search roots)
2. **Parses child DWGs** through the same backend, recursively up to `max_xref_depth`
3. **Caches** parsed results to avoid re-parsing shared xrefs
4. **Detects cycles** by tracking resolved paths in a visited set — cycle-blocked sources get `parse_status="unresolved"` and an `xref-cycle` warning
5. **Records missing xrefs** as `SourceDocument` entries with `parse_status="missing"`, `MissingReference` records, and warnings

After resolution, the document contains all reachable sources, a complete xref graph, and full missing-reference reporting.

## Stage 3: Composition

**Module:** `pipeline/compose.py`  
**Enabled by:** `bind_xrefs=True`

The `CompositionBuilder` creates one `Composition` per root drawing (extensible to per-layout in the future):

1. Iterates over all sources and creates `SourceBinding` entries
2. **Propagates transform chains** by walking up the parent chain for each source
3. Collects entity refs from all sources
4. Marks missing sources in `missing_source_ids`
5. Sets `completeness_status` to `"missing_dependencies"` if any bindings are incomplete

## Stage 4: Confidence computation

**Module:** `pipeline/confidence.py`

`compute_confidence()` mutates `interpretation_confidence` in-place:

- Applies fixed penalties per missing xref, failed xref, cycle-blocked reference
- Applies small penalties per unsupported entity type
- Applies capped penalties for generic backend warnings
- Calls `recompute()` to derive the final value and explanation

## Stage 5: Completeness and export

After confidence computation:

1. `CompletenessReport.recompute_from_document()` tallies missing, unresolved, failed, and cycle-blocked xref counts
2. `derive_interpretation_status()` combines completeness and confidence into a single `interpretation_status`
3. Parser options are recorded in `metadata`
4. If `out_dir` is set, `export_json_file()` writes the canonical JSON with deterministic sorting

## Disabling stages

```python
# Parse only — no xref resolution, no composition
result = parser.parse(path, ParseOptions(
    resolve_xrefs=False,
    bind_xrefs=False,
))

# Resolve xrefs but don't build compositions
result = parser.parse(path, ParseOptions(
    resolve_xrefs=True,
    bind_xrefs=False,
))
```

Disabling stages reduces processing time and output size but produces incomplete graph/composition data.
