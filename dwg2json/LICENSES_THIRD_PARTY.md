# Third-Party Licenses

This file records all third-party components used by dwg2json, their license terms, and how they are integrated.

## Runtime Dependencies (pip)

| Component | License | Integration | Notes |
|-----------|---------|-------------|-------|
| pydantic | MIT | pip dependency | Schema enforcement and serialisation |
| orjson | MIT / Apache-2.0 | pip dependency | Fast JSON serialisation |
| typer | MIT | pip dependency | CLI framework |
| rich | MIT | pip dependency | Terminal output formatting |
| typing-extensions | PSF | pip dependency | Backport type hints |
| ezdxf | MIT | pip dependency | DXF parsing after DWG → DXF conversion |

## System Dependencies

| Component | License | Integration | Notes |
|-----------|---------|-------------|-------|
| LibreDWG | GPL-3.0-or-later | Shell-invoked (`dwg2dxf` CLI) | DWG binary decoding. Not linked, not vendored. Invoked as a subprocess. The dwg2json package itself is AGPL-3.0-or-later which is compatible with GPL-3.0-or-later for this usage pattern. |

## Dev Dependencies

| Component | License | Integration | Notes |
|-----------|---------|-------------|-------|
| pytest | MIT | pip dev dependency | Test framework |
| pytest-cov | MIT | pip dev dependency | Coverage reporting |
| ruff | MIT | pip dev dependency | Linter and formatter |
| mypy | MIT | pip dev dependency | Static type checking |

## License Compatibility Notes

- dwg2json is licensed under AGPL-3.0-or-later.
- All pip runtime dependencies use permissive licenses (MIT, Apache-2.0, PSF) and are compatible with AGPL-3.0-or-later.
- LibreDWG is GPL-3.0-or-later. It is invoked as a separate process (subprocess), not linked or vendored. This usage pattern is compatible with our AGPL-3.0-or-later license.
- No upstream code is copied or vendored into this repository.
