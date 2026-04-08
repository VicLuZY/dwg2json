from __future__ import annotations

from pathlib import Path

import orjson

from ..models import ParseOptions, ParseResult


def export_json_file(result: ParseResult, options: ParseOptions) -> Path:
    source_path = result.source_path
    output_dir = Path(options.out_dir) if options.out_dir else source_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{source_path.name}.json"
    output_path.write_bytes(orjson.dumps(result.document.model_dump(), option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS))
    return output_path
