"""Tests for the null backend."""

from pathlib import Path

from dwg2json.backends.null_backend import NullBackend
from dwg2json.models import ParseOptions


class TestNullBackend:
    def test_parse_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.dwg"
        f.write_bytes(b"\x00")

        backend = NullBackend()
        result = backend.parse(f, ParseOptions())

        assert result.document.root_source.exists is True
        assert result.document.root_source.parsed is True
        assert result.document.root_source.parse_status == "parsed"
        assert result.document.parser.backend == "null"

    def test_parse_nonexistent_file(self, tmp_path: Path) -> None:
        f = tmp_path / "missing.dwg"

        backend = NullBackend()
        result = backend.parse(f, ParseOptions())

        assert result.document.root_source.exists is False
        assert result.document.root_source.parse_status == "failed"

    def test_has_model_layout(self, tmp_path: Path) -> None:
        f = tmp_path / "test.dwg"
        f.write_bytes(b"\x00")

        backend = NullBackend()
        result = backend.parse(f, ParseOptions())

        layouts = result.document.root_source.layouts
        assert len(layouts) >= 1
        assert any(la.is_model_space for la in layouts)

    def test_xref_graph_has_root_node(self, tmp_path: Path) -> None:
        f = tmp_path / "test.dwg"
        f.write_bytes(b"\x00")

        backend = NullBackend()
        result = backend.parse(f, ParseOptions())

        assert len(result.document.xref_graph.nodes) == 1
        node = result.document.xref_graph.nodes[0]
        assert node.depth == 0

    def test_is_available(self) -> None:
        assert NullBackend().is_available() is True

    def test_produces_info_warning(self, tmp_path: Path) -> None:
        f = tmp_path / "test.dwg"
        f.write_bytes(b"\x00")

        backend = NullBackend()
        result = backend.parse(f, ParseOptions())

        assert any(w.code == "null-backend" for w in result.document.root_source.warnings)
