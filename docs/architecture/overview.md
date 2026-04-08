# Architecture Overview

## Design center

The product contract is intentional and narrow:

- **One root DWG in** — a single designated drawing is the parse root
- **One canonical JSON out** — exactly one `DwgJsonDocument` per invocation

Everything else — backends, xref resolution, composition, confidence heuristics — serves that contract.

## Two-layer truth model

The canonical JSON deliberately encodes two complementary views.

### Source truth

Each physical DWG file (root or xref) is preserved as a `SourceDocument` with its own layers, layouts, blocks, entities, and warnings. Source truth answers: *What did we read from each file, and in what state?*

### Composition truth

`Composition` records describe how multiple sources should be interpreted together in one coordinate frame. Source bindings carry placement transforms, inherited transform chains, and entity references. Composition truth answers: *How should a consumer interpret the combined scene?*

These layers are both first-class. Downstream tools should use source truth for per-file analytics and composition truth for spatially coupled semantics.

## Module layout

```
src/dwg2json/
├── __init__.py          # Public API surface
├── api.py               # Dwg2JsonParser — orchestration
├── cli.py               # Typer CLI
├── models.py            # Pydantic v2 canonical models
├── backends/
│   ├── base.py          # Abstract DwgBackend
│   ├── null_backend.py  # Empty-but-valid results
│   ├── libredwg_backend.py  # LibreDWG + ezdxf
│   └── registry.py      # Backend lookup
├── pipeline/
│   ├── xref_paths.py    # Path candidate resolution
│   ├── xrefs.py         # Recursive xref resolver
│   ├── compose.py       # Composition builder
│   ├── confidence.py    # Confidence heuristics
│   └── export_json.py   # Deterministic JSON export
├── schema/
│   └── __init__.py      # JSON Schema generation & validation
└── native/
    ├── bridge.py         # Future native binding placeholder
    └── capabilities.py   # Backend capability introspection
```

## Data flow

```
DWG file
  │
  ▼
┌─────────────────┐
│  Backend Parse   │  Layer 2: DwgBackend.parse()
│  (LibreDWG/null) │  → SourceDocument + raw_xrefs
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Xref Resolver   │  Layer 4: resolve paths, parse children,
│                   │  detect cycles, record missing
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Composition     │  Layer 4: bind sources into composed
│  Builder         │  contexts with transform chains
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Confidence &    │  Compute penalties, recompute completeness,
│  Completeness    │  derive interpretation_status
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  JSON Export     │  Deterministic sorting, OPT_SORT_KEYS,
│                   │  write <name>.dwg.json
└─────────────────┘
```
