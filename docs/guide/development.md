# Development

## Repository layout

| Path | Role |
|------|------|
| `dwg2json/` | Python package (installable with `pip install -e ".[dev]"` from this directory) |
| `docs/` | VitePress documentation site source |
| `scripts/` | Repo-root helpers (fetch test DWGs, batch parse) |
| `local_dwg_samples/` | **Gitignored** — downloaded `.dwg` binaries for local integration testing |

## Environment setup

```bash
cd dwg2json
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quality checks

```bash
ruff check .
mypy src/dwg2json
pytest
pytest --cov=dwg2json --cov-report=term-missing
```

Configuration lives in `dwg2json/pyproject.toml` (`tool.ruff`, `tool.mypy`, `tool.pytest`).

## LibreDWG / `dwg2dxf`

The **libredwg** backend shells out to `dwg2dxf`. If the binary is not on `PATH`, set:

```bash
export DWG2JSON_DWG2DXF=/full/path/to/dwg2dxf
```

On some Linux distributions the `libredwg-utils` package is unavailable or outdated; building from the [LibreDWG releases](https://github.com/LibreDWG/libredwg/releases) is a reliable fallback. The repository workflow **DWG corpus smoke** (`.github/workflows/dwg_corpus.yml`) documents one way to compile and run batch tests in CI.

## Bulk test drawings (optional)

Never commit downloaded `.dwg` files. From the **monorepo root**:

```bash
python scripts/fetch_libredwg_test_dwgs.py --dest local_dwg_samples
python scripts/batch_parse_dwgs.py --root local_dwg_samples --out-report local_dwg_samples/parse_report.json
```

The report JSON lists per-file success, entity counts, and error messages for debugging.

## Continuous integration

- **CI** (`.github/workflows/ci.yml`) — `ruff`, `mypy`, `pytest` on Python 3.11 and 3.12.
- **Docs** (`.github/workflows/docs.yml`) — builds and deploys this site to GitHub Pages.
- **DWG corpus** (`.github/workflows/dwg_corpus.yml`) — manual or weekly; downloads upstream test DWGs and batch-parses with a runner-built `dwg2dxf`.
