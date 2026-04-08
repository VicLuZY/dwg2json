"""Shared test fixtures for dwg2json."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dwg2json.backends.base import DwgBackend
from dwg2json.models import (
    DwgJsonDocument,
    Entity,
    Layer,
    Layout,
    ParseOptions,
    ParseResult,
    ParserInfo,
    SourceDocument,
    WarningRecord,
    XrefGraphNode,
)


class FakeBackend(DwgBackend):
    """Configurable fake backend for testing the pipeline.

    ``xref_map`` maps a DWG stem name to a list of raw xref declarations.
    ``entity_map`` maps a DWG stem name to a list of Entity objects.
    ``layer_map`` maps a DWG stem name to a list of Layer objects.
    """

    name = "fake"
    version = "test"

    def __init__(
        self,
        xref_map: dict[str, list[dict[str, Any]]] | None = None,
        entity_map: dict[str, list[Entity]] | None = None,
        layer_map: dict[str, list[Layer]] | None = None,
        extra_layouts: list[Layout] | None = None,
    ) -> None:
        self.xref_map = xref_map or {}
        self.entity_map = entity_map or {}
        self.layer_map = layer_map or {}
        self.extra_layouts = extra_layouts or []

    def parse(self, path: Path, options: ParseOptions) -> ParseResult:
        root_id = f"src-{path.stem}"
        raw_xrefs = self.xref_map.get(path.stem, [])
        entities = self.entity_map.get(path.stem, [
            Entity(
                id=f"{root_id}-e1",
                source_id=root_id,
                handle="10",
                type="LINE",
                layout="Model",
                space_class="model",
            ),
        ])
        layers = self.layer_map.get(path.stem, [
            Layer(id=f"{root_id}__layer_0", name="0"),
        ])

        base_layouts = [
            Layout(id=f"{root_id}__model", name="Model", is_model_space=True, tab_order=0),
        ]
        extra = list(self.extra_layouts)
        layouts: list[Layout] = []
        for i, ly in enumerate(base_layouts + extra):
            layouts.append(ly.model_copy(update={"tab_order": i}))

        source = SourceDocument(
            id=root_id,
            path=str(path),
            resolved_path=str(path.resolve()),
            role="root",
            exists=True,
            parsed=True,
            parse_status="parsed",
            metadata={"raw_xrefs": raw_xrefs},
            layers=layers,
            layouts=layouts,
            blocks=[],
            entities=entities,
            warnings=[
                WarningRecord(
                    code="fake",
                    message="fake backend",
                    source_id=root_id,
                    severity="info",
                ),
            ],
        )
        document = DwgJsonDocument(
            parser=ParserInfo(backend=self.name, backend_version=self.version),
            root_source_id=root_id,
            sources=[source],
            warnings=list(source.warnings),
        )
        document.xref_graph.nodes.append(
            XrefGraphNode(
                source_id=root_id,
                path=str(path),
                resolved_path=str(path.resolve()),
                depth=0,
            )
        )
        return ParseResult(document=document)


@pytest.fixture
def fake_backend() -> FakeBackend:
    return FakeBackend()


@pytest.fixture
def tmp_dwg(tmp_path: Path) -> Path:
    """Create a stub DWG file for testing."""
    dwg = tmp_path / "test.dwg"
    dwg.write_bytes(b"\x00" * 64)
    return dwg


@pytest.fixture
def tmp_dwg_with_xref(tmp_path: Path) -> tuple[Path, Path]:
    """Create a root DWG and a resolved xref DWG."""
    root = tmp_path / "root.dwg"
    root.write_bytes(b"\x00" * 64)
    bg = tmp_path / "bg.dwg"
    bg.write_bytes(b"\x00" * 64)
    return root, bg


@pytest.fixture
def tmp_dwg_missing_xref(tmp_path: Path) -> Path:
    """Create a root DWG whose xref target does NOT exist."""
    root = tmp_path / "root.dwg"
    root.write_bytes(b"\x00" * 64)
    return root
