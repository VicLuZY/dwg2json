# dwg2json

Python-callable seed package for converting a DWG and its bound xref context into one canonical JSON file.

## Package identity

- PyPI distribution: `dwg2json`
- Python import: `dwg2json`
- CLI: `dwg2json`

## Product boundary

This package is **not** a multi-output converter.

It produces **one canonical JSON file** per root DWG.

That JSON must preserve:

- document metadata
- layers
- blocks
- block references
- entities
- handles
- transforms
- layouts
- xrefs
- xref binding/composition context
- missing xref status
- warnings
- provenance
- completeness status

## Xref policy

Xrefs are not interpreted as isolated child drawings.

They are treated as bound composition dependencies.

Example:
A device layout over a background xref only makes sense when the overlay and the background are interpreted together in the same coordinate frame.

Therefore the canonical JSON model includes:

- source documents
- xref dependency edges
- xref placements
- composed contexts where host and xref content are bound together
- completeness flags when one or more xrefs are missing or broken

If an xref is missing, the output JSON must explicitly state that information content is partial and downstream consumers must treat it as incomplete.

## Current status

This is a seed source package.

It gives you:

- Python API
- backend adapter interface
- LibreDWG-oriented placeholder backend
- canonical JSON models
- xref binding and missing-xref completeness scaffolding
- one-file JSON exporter
- CLI entrypoint
- detailed `DEVELOPMENT_PLAN.txt` for Codex

It does **not** yet include a production DWG decoder.

The runtime control surface is Python, but the decoding core may be implemented in Python, Rust, C++, or C as long as it is packaged behind a stable Python API.

## Install

```bash
pip install -e .[dev]
```

## Example

```python
from pathlib import Path
from dwg2json import Dwg2JsonParser, ParseOptions

parser = Dwg2JsonParser()
result = parser.parse(
    Path("example.dwg"),
    options=ParseOptions(resolve_xrefs=True, bind_xrefs=True, max_xref_depth=8),
)

result.write_json_file()
print(result.output_json_path)
print(result.document.completeness.status)
```

## CLI

```bash
dwg2json parse ./drawing.dwg --out ./out --resolve-xrefs --bind-xrefs --max-xref-depth 8
```

## Output

Default output file name:

```text
<drawing>.dwg.json
```

## Architecture

Core pipeline:

1. ingest root DWG with a backend
2. normalize to canonical source and entity models
3. discover and resolve xrefs
4. bind host and xref placements into composed contexts
5. mark completeness if dependencies are missing
6. export one canonical JSON file

## License

AGPL-3.0-or-later
