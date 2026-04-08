# dwg2json

`dwg2json` is a Python-callable, open-source DWG semantic deparser that emits **one canonical JSON file per root DWG**.

## Scope

- Parse DWG into one JSON document.
- Preserve CAD semantics.
- Bind xref overlays into composite interpretation contexts.
- Report missing or broken xrefs explicitly.
- Keep provenance and uncertainty visible.
- Allow native implementation in C, C++, or Rust behind a Python API.

## Non-goals

- Not a multi-output converter.
- Not a viewer.
- Not a renderer-first product.
- Not a promise of perfect support for every proprietary DWG edge case in v1.

## Install

```bash
pip install -e .
```

## CLI

```bash
dwg2json input.dwg -o input.dwg.json
```

## Python

```python
from dwg2json import Dwg2JsonParser

parser = Dwg2JsonParser()
doc = parser.parse_file("input.dwg")
print(doc.schema_version)
```
