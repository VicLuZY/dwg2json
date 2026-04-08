# Third-Party Licenses

dwg2json is licensed under **AGPL-3.0-or-later**.

This page records all third-party components, their license terms, and how they are integrated.

## Runtime dependencies (pip)

| Component | License | Integration | Notes |
|-----------|---------|-------------|-------|
| pydantic | MIT | pip dependency | Schema enforcement and serialisation |
| orjson | MIT / Apache-2.0 | pip dependency | Fast JSON serialisation |
| typer | MIT | pip dependency | CLI framework |
| rich | MIT | pip dependency | Terminal output formatting |
| typing-extensions | PSF | pip dependency | Backport type hints |
| ezdxf | MIT | pip dependency | DXF parsing after DWG conversion |

## System dependencies

| Component | License | Integration | Notes |
|-----------|---------|-------------|-------|
| LibreDWG | GPL-3.0-or-later | Shell-invoked (`dwg2dxf` CLI) | DWG binary decoding. Not linked, not vendored. Invoked as a subprocess. |

## Dev dependencies

| Component | License | Integration | Notes |
|-----------|---------|-------------|-------|
| pytest | MIT | pip dev dependency | Test framework |
| pytest-cov | MIT | pip dev dependency | Coverage reporting |
| ruff | MIT | pip dev dependency | Linter and formatter |
| mypy | MIT | pip dev dependency | Static type checking |
| jsonschema | MIT | pip dev dependency | Schema validation |
| VitePress | MIT | npm dev dependency | Documentation site generator |

## License compatibility

- dwg2json is **AGPL-3.0-or-later**.
- All pip runtime dependencies use permissive licenses (MIT, Apache-2.0, PSF) compatible with AGPL-3.0-or-later.
- LibreDWG is **GPL-3.0-or-later**. It is invoked as a separate process (subprocess), not linked or vendored. This usage pattern is compatible with AGPL-3.0-or-later.
- No upstream code is copied or vendored into this repository.

The full license text is available in the repository's `LICENSE` file.
