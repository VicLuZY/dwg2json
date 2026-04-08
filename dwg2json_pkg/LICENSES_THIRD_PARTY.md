# Third-party code and dependency ledger

This project is intentionally designed to allow reuse of open-source code and dependencies,
provided their licenses are respected.

## Rules

1. Every third-party dependency must be listed here.
2. Every copied source file must retain its original copyright and license notice.
3. Incompatible licenses must not be mixed into the same distribution artifact.
4. Dynamic or optional adapters must be isolated when needed.
5. Canonical schema and original code should remain clearly attributable.

## Candidate upstreams to evaluate

- LibreDWG
- ACadSharp
- libdxfrw
- Other permissively or copyleft licensed CAD parsing components

## Required metadata per dependency

- Name
- Version or commit
- Source URL
- License
- Linkage mode
- Files copied or linked
- Local modifications
- Obligations
- Compatibility assessment
- Whether bundled, optional, or build-time only
