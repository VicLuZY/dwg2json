#!/usr/bin/env python3
"""Download LibreDWG upstream test DWGs (GPL-3.0-or-later corpus) for local parsing.

Writes under ``local_dwg_samples/`` at the repository root by default.
That directory is gitignored — never commit downloaded binaries.

Also fetches a few small ``.dwg`` files from the ezdxf repository (MIT).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


LIBREDWG_TREE_API = (
    "https://api.github.com/repos/LibreDWG/libredwg/git/trees/master?recursive=1"
)
LIBREDWG_RAW = "https://raw.githubusercontent.com/LibreDWG/libredwg/master"

EZDXF_EXTRA = [
    "docs/graphics/dim_linear_tutorial.dwg",
    "docs/graphics/dim_radial_tutorial.dwg",
    "docs/graphics/dimstyle-vars.dwg",
    "docs/graphics/dimtad-dimjust.dwg",
    "tests/test_08_addons/807_1.dwg",
]
EZDXF_RAW = "https://raw.githubusercontent.com/mozman/ezdxf/master"


def _github_headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "User-Agent": "dwg2json-fetch-test-dwgs",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def list_libredwg_dwgs() -> list[str]:
    req = urllib.request.Request(LIBREDWG_TREE_API, headers=_github_headers())
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
        data = json.load(resp)
    paths: list[str] = []
    for item in data.get("tree", []):
        p = item.get("path", "")
        if p.lower().endswith(".dwg"):
            paths.append(p)
    paths.sort()
    return paths


def download_one(url: str, dest: Path) -> tuple[str, str | None]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return str(dest), None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "dwg2json-fetch-test-dwgs"})
        with urllib.request.urlopen(req, timeout=180) as resp:  # noqa: S310
            dest.write_bytes(resp.read())
    except (OSError, urllib.error.URLError) as e:
        return str(dest), str(e)
    return str(dest), None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "local_dwg_samples",
        help="Output root directory (default: repo root / local_dwg_samples)",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=8,
        help="Parallel download workers",
    )
    parser.add_argument(
        "--libredwg-only",
        action="store_true",
        help="Skip ezdxf repository samples",
    )
    args = parser.parse_args()
    dest_root: Path = args.dest

    tasks: list[tuple[str, Path]] = []
    for rel in list_libredwg_dwgs():
        url = f"{LIBREDWG_RAW}/{rel}"
        safe = rel.replace("/", "__")
        tasks.append((url, dest_root / "libredwg" / safe))

    if not args.libredwg_only:
        for rel in EZDXF_EXTRA:
            url = f"{EZDXF_RAW}/{rel}"
            safe = rel.replace("/", "__")
            tasks.append((url, dest_root / "ezdxf" / safe))

    errors: list[str] = []
    ok = 0
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        futs = {ex.submit(download_one, u, p): (u, p) for u, p in tasks}
        for fut in as_completed(futs):
            path, err = fut.result()
            if err:
                errors.append(f"{path}: {err}")
            else:
                ok += 1

    print(f"Downloaded (or skipped existing): {ok} files -> {dest_root}")
    if errors:
        print(f"Failures: {len(errors)}", file=sys.stderr)
        for line in errors[:50]:
            print(line, file=sys.stderr)
        if len(errors) > 50:
            print(f"... and {len(errors) - 50} more", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
