# dwg2json repository

This repository contains the `dwg2json` Python package, the VitePress docs site, and helper scripts.

## Repository map

- `dwg2json/` — canonical Python package (source, tests, examples, packaging metadata)
- `docs/` — VitePress documentation source, deployed to GitHub Pages
- `scripts/` — repository-level helpers (DWG corpus fetch and batch parse)
- `.github/workflows/` — CI, docs deploy, and DWG corpus workflows
- `local_dwg_samples/` — local downloaded DWG fixtures (**gitignored**)

## Quick start

```bash
cd dwg2json
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run checks:

```bash
cd ..
make lint
make typecheck
make test
make docs-build
```

## More docs

- Package docs: `dwg2json/README.md`
- Architecture: `dwg2json/docs/ARCHITECTURE.md`
- Site: [https://vicluzy.github.io/dwg2json/](https://vicluzy.github.io/dwg2json/)
- Contribution guide: `CONTRIBUTING.md`
