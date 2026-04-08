#!/usr/bin/env python3
"""Parse every ``*.dwg`` under a directory with dwg2json (LibreDWG backend).

Requires ``dwg2dxf`` on PATH or ``DWG2JSON_DWG2DXF`` pointing to the binary.
Install: ``pip install -e dwg2json/[dev]`` from the ``dwg2json`` package dir.

Writes a JSON report (default: alongside the scan root, name ``parse_report.json``).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    pkg_src = repo_root / "dwg2json" / "src"
    if pkg_src.is_dir():
        sys.path.insert(0, str(pkg_src))

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=repo_root / "local_dwg_samples",
        help="Directory tree to scan for .dwg files",
    )
    parser.add_argument(
        "--out-report",
        type=Path,
        default=None,
        help="JSON report path (default: <root>/parse_report.json)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max files to parse (0 = no limit)",
    )
    args = parser.parse_args()

    from dwg2json import Dwg2JsonParser, ParseOptions
    from dwg2json.backends.libredwg_backend import LibreDwgBackend

    root: Path = args.root.resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2

    backend = LibreDwgBackend()
    if not backend.is_available():
        print(
            "LibreDWG dwg2dxf not found. Set DWG2JSON_DWG2DXF or install "
            "libredwg-utils (e.g. apt install libredwg-utils on Debian/Ubuntu).",
            file=sys.stderr,
        )
        return 3

    dwgs = sorted(root.rglob("*.dwg"))
    if args.limit:
        dwgs = dwgs[: args.limit]

    report_path = args.out_report or (root / "parse_report.json")
    parser_obj = Dwg2JsonParser(backend=backend)
    opts = ParseOptions(
        resolve_xrefs=True,
        bind_xrefs=True,
        max_xref_depth=4,
        missing_xref_policy="record",
    )

    rows: list[dict] = []
    t0 = time.perf_counter()
    for i, path in enumerate(dwgs):
        rel = str(path.relative_to(root))
        row: dict = {"file": rel, "abs": str(path)}
        t_parse = time.perf_counter()
        try:
            result = parser_obj.parse(path, opts)
            doc = result.document
            root_src = doc.root_source
            row["ok"] = True
            row["parse_status"] = root_src.parse_status if root_src else None
            row["entity_count"] = len(doc.all_entities)
            row["sources"] = len(doc.sources)
            row["interpretation_status"] = doc.interpretation_status
            row["warnings"] = len(doc.warnings)
        except Exception as e:  # noqa: BLE001 — intentional harness catch-all
            row["ok"] = False
            row["error"] = f"{type(e).__name__}: {e}"
            row["traceback"] = traceback.format_exc()
        row["seconds"] = round(time.perf_counter() - t_parse, 3)
        rows.append(row)
        if (i + 1) % 20 == 0:
            print(f"Progress {i + 1}/{len(dwgs)}", file=sys.stderr)

    summary = {
        "root": str(root),
        "total": len(rows),
        "ok": sum(1 for r in rows if r.get("ok")),
        "failed": sum(1 for r in rows if not r.get("ok")),
        "wall_seconds": round(time.perf_counter() - t0, 2),
        "results": rows,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))
    print(f"Wrote {report_path}")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
