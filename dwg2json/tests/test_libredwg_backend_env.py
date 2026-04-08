"""Tests for LibreDWG backend environment configuration."""

from __future__ import annotations

from dwg2json.backends.libredwg_backend import LibreDwgBackend


def test_env_dwg2dxf_path_used(monkeypatch, tmp_path) -> None:
    stub = tmp_path / "dwg2dxf"
    stub.write_text("#!/bin/sh\necho stub 0.1\n")
    stub.chmod(0o755)
    monkeypatch.setenv("DWG2JSON_DWG2DXF", str(stub))
    backend = LibreDwgBackend()
    assert backend.is_available()
    assert backend._dwg2dxf == str(stub)


def test_env_dwg2dxf_missing_file_then_no_path(monkeypatch) -> None:
    monkeypatch.setenv("DWG2JSON_DWG2DXF", "/nonexistent/dwg2dxf-binary")
    monkeypatch.setattr(
        "dwg2json.backends.libredwg_backend.shutil.which",
        lambda _name: None,
    )
    backend = LibreDwgBackend()
    assert not backend.is_available()
    assert backend._dwg2dxf is None
