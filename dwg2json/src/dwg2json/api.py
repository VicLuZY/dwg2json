"""Public Python API for dwg2json.

Usage::

    from dwg2json import Dwg2JsonParser, ParseOptions

    parser = Dwg2JsonParser()
    result = parser.parse(Path("input.dwg"))
    result.write_json_file()
"""

from __future__ import annotations

from pathlib import Path

from .backends.base import DwgBackend
from .backends.registry import get_backend
from .models import DwgJsonDocument, ParseOptions, ParseResult
from .pipeline.compose import CompositionBuilder
from .pipeline.confidence import compute_confidence
from .pipeline.export_json import export_json_file, to_json_text
from .pipeline.xrefs import XrefResolver


class Dwg2JsonParser:
    """Main entry point.  Wraps a backend + the canonical pipeline."""

    def __init__(self, backend: DwgBackend | str | None = None) -> None:
        if isinstance(backend, str):
            self.backend = get_backend(backend)
        elif backend is None:
            self.backend = get_backend("auto")
        else:
            self.backend = backend

    # ------------------------------------------------------------------
    # High-level convenience methods (from development plan)
    # ------------------------------------------------------------------

    def parse_file(self, path: str | Path, **kwargs) -> DwgJsonDocument:
        """Parse a DWG and return the canonical document model."""
        result = self.parse(Path(path), ParseOptions(**kwargs) if kwargs else None)
        return result.document

    def parse_to_json_text(self, path: str | Path, indent: int = 2, **kwargs) -> str:
        """Parse a DWG and return the canonical JSON as a string."""
        opts = ParseOptions(indent=indent, **kwargs)
        result = self.parse(Path(path), opts)
        return to_json_text(result, indent=indent)

    def parse_to_json_file(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        indent: int = 2,
        **kwargs,
    ) -> str:
        """Parse a DWG and write the canonical JSON file.  Returns the output path."""
        out_dir = str(Path(output_path).parent) if output_path else None
        opts = ParseOptions(out_dir=out_dir, indent=indent, **kwargs)
        result = self.parse(Path(input_path), opts)
        if output_path:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(to_json_text(result, indent=indent), encoding="utf-8")
            result.output_json_path = str(target)
            return str(target)
        path = export_json_file(result, opts)
        result.output_json_path = str(path)
        return str(path)

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    def parse(self, path: Path, options: ParseOptions | None = None) -> ParseResult:
        options = options or ParseOptions()
        result = self.backend.parse(path, options)

        if options.resolve_xrefs:
            resolver = XrefResolver(self.backend)
            result = resolver.resolve(result, options)

        if options.bind_xrefs:
            composer = CompositionBuilder()
            result = composer.bind(result, options)

        # Confidence and completeness
        compute_confidence(result.document)
        result.document.completeness.recompute_from_document(result.document)
        result.document.interpretation_status = result.document.derive_interpretation_status()

        # Record parser options in metadata
        result.document.metadata["parser_options"] = options.model_dump(mode="json")

        # Export if out_dir is set
        if options.out_dir:
            output_path = export_json_file(result, options)
            result.output_json_path = str(output_path)

        return result
