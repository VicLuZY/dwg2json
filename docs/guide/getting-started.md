# Getting Started

**dwg2json** converts a single root DWG into one canonical JSON file. External references (xrefs) are treated as bound composition dependencies — parsed, resolved, and placed into shared coordinate frames — so downstream systems can reason over the combined scene.

## Quick install

```bash
pip install dwg2json
```

For real DWG decoding you also need **LibreDWG** installed on your system (the `dwg2dxf` binary must be on `$PATH`). See [Installation](./installation) for details.

## Minimal example

```python
from pathlib import Path
from dwg2json import Dwg2JsonParser, ParseOptions

parser = Dwg2JsonParser()
result = parser.parse(
    Path("drawing.dwg"),
    ParseOptions(
        resolve_xrefs=True,
        bind_xrefs=True,
        out_dir="./out",
    ),
)

print(result.output_json_path)          # ./out/drawing.dwg.json
print(result.document.completeness.status)  # "complete" or "partial"
print(result.document.interpretation_confidence.value)  # 0.0–1.0
```

The output file `drawing.dwg.json` contains:

- Document metadata and provenance
- Per-source layers, layouts, blocks, entities
- Xref dependency graph
- Composed spatial contexts
- Completeness and confidence signals
- Structured warnings and missing-reference records

## CLI quick start

```bash
# Parse a DWG and write canonical JSON
dwg2json parse ./drawing.dwg --out ./out

# Inspect without full xref resolution
dwg2json info ./drawing.dwg

# Dump the JSON Schema
dwg2json schema > dwg2json.schema.json

# Validate an existing output file
dwg2json validate ./out/drawing.dwg.json
```

## What happens when xrefs are missing?

Missing xrefs are the norm in real project archives. dwg2json does **not** silently pretend the drawing is complete. Instead:

- The xref graph still records the dependency edge
- A `MissingReference` entry is emitted
- The composition is marked `missing_dependencies`
- Top-level `completeness.status` becomes `partial`
- `interpretation_confidence` decreases
- A `consumer_caution` string explains the impact

See [Xref Policy](./xref-policy) and [Confidence & Completeness](./confidence) for full details.
