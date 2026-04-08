# Contributing

## Project structure

Use `dwg2json/` as the single package source of truth.

- Runtime code: `dwg2json/src/dwg2json/`
- Tests: `dwg2json/tests/`
- User/package docs: `dwg2json/README.md`
- Site docs: `docs/`

## Local setup

```bash
cd dwg2json
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quality gates

From repository root:

```bash
make lint
make typecheck
make test
make docs-build
```

Or directly:

```bash
cd dwg2json
ruff check .
mypy src/dwg2json
pytest
```

## DWG corpus testing

Downloaded DWG fixtures must never be committed. Use `local_dwg_samples/` (already gitignored):

```bash
python scripts/fetch_libredwg_test_dwgs.py --dest local_dwg_samples
python scripts/batch_parse_dwgs.py --root local_dwg_samples
```

Requires `dwg2dxf` (or `DWG2JSON_DWG2DXF` set to a binary path).
