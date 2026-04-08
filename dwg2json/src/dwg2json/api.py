from __future__ import annotations

from pathlib import Path

from .backends.base import DwgBackend
from .backends.libredwg_backend import LibreDwgBackend
from .models import ParseOptions, ParseResult
from .pipeline.compose import CompositionBuilder
from .pipeline.export_json import export_json_file
from .pipeline.xrefs import XrefResolver


class Dwg2JsonParser:
    def __init__(self, backend: DwgBackend | None = None) -> None:
        self.backend = backend or LibreDwgBackend()

    def parse(self, path: Path, options: ParseOptions | None = None) -> ParseResult:
        options = options or ParseOptions()
        result = self.backend.parse(path, options)

        if options.resolve_xrefs:
            resolver = XrefResolver(self.backend)
            result = resolver.resolve(result, options)

        if options.bind_xrefs:
            composer = CompositionBuilder()
            result = composer.bind(result, options)

        result.document.metadata.setdefault("parser_options", options.model_dump())
        result.document.completeness.recompute_from_document(result.document)

        output_path = export_json_file(result, options) if options.out_dir else None
        result.output_json_path = str(output_path) if output_path else None
        return result
