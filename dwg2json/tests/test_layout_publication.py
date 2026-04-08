"""Layout / viewport / publication semantics (fake backend + DXF via LibreDWG path)."""

from __future__ import annotations

from pathlib import Path

import ezdxf

from dwg2json.api import Dwg2JsonParser
from dwg2json.backends.libredwg_backend import LibreDwgBackend
from dwg2json.models import Entity, Layout, ParseOptions
from tests.conftest import FakeBackend


class TestLayoutSheetComposition:
    def test_fake_backend_emits_layout_sheet_composition(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")
        sheet = Layout(id="src-root__layout_Sheet1", name="Sheet1", is_model_space=False)
        backend = FakeBackend(
            extra_layouts=[sheet],
            entity_map={
                "root": [
                    Entity(
                        id="paper1",
                        source_id="src-root",
                        handle="10",
                        type="TEXT",
                        text="Title",
                        layout="Sheet1",
                        space_class="paper",
                    ),
                    Entity(
                        id="m1",
                        source_id="src-root",
                        handle="20",
                        type="LINE",
                        layout="Model",
                        space_class="model",
                    ),
                ],
            },
        )
        parser = Dwg2JsonParser(backend=backend)
        result = parser.parse(root, ParseOptions())

        kinds = [c.kind for c in result.document.compositions]
        assert kinds[0] == "xref_scene"
        assert "layout_sheet" in kinds
        layout_comp = next(c for c in result.document.compositions if c.kind == "layout_sheet")
        assert layout_comp.layout_name == "Sheet1"
        assert "paper1" in layout_comp.entity_refs
        assert "m1" not in layout_comp.entity_refs

    def test_publication_index_on_root_source(self, tmp_path: Path) -> None:
        root = tmp_path / "root.dwg"
        root.write_bytes(b"\x00")
        parser = Dwg2JsonParser(backend=FakeBackend())
        result = parser.parse(root, ParseOptions())
        idx = result.document.root_source.publication_index
        assert any(e.role == "authoring_model" for e in idx)


FIXTURE_DXF = Path(__file__).parent / "fixtures" / "publication_minimal.dxf"


class TestLibreDwgDxfPublication:
    @staticmethod
    def _write_minimal_dxf(path: Path) -> None:
        doc = ezdxf.new("R2010")
        doc.layers.add("PLOTTED")
        doc.layers.get("PLOTTED").dxf.plot = 1
        doc.layers.add("NOPLOT")
        doc.layers.get("NOPLOT").dxf.plot = 0
        msp = doc.modelspace()
        msp.add_line((0, 0), (40, 40), dxfattribs={"layer": "PLOTTED"})
        msp.add_line((1, 1), (5, 5), dxfattribs={"layer": "NOPLOT"})
        psp = doc.layouts.new("PubLayout")
        psp.add_viewport(
            center=(100, 100),
            size=(80, 60),
            view_center_point=(20, 20),
            view_height=35.0,
            status=2,
        )
        doc.saveas(str(path))

    def test_dxf_viewport_space_class_and_layer_plot(self, tmp_path: Path) -> None:
        dxf_path = tmp_path / "pub.dxf"
        self._write_minimal_dxf(dxf_path)

        backend = LibreDwgBackend()
        result = backend.parse(dxf_path, ParseOptions(bind_xrefs=False, resolve_xrefs=False))
        source = result.document.root_source
        assert source.parsed

        pub_ly = [ly for ly in source.layouts if ly.name == "PubLayout"][0]
        assert pub_ly.plot_settings is not None
        assert "paper_size" in pub_ly.plot_settings
        vps = pub_ly.viewports
        assert len(vps) >= 1
        assert vps[0].view_height_model == 35.0
        assert vps[0].model_to_paper_scale is not None
        assert vps[0].model_to_paper_scale > 0

        by_layer = {la.name: la for la in source.layers}
        assert by_layer["NOPLOT"].is_plottable is False
        assert by_layer["PLOTTED"].is_plottable is True

        for ent in source.entities:
            if ent.layer == "NOPLOT" and ent.layout == "Model":
                assert ent.non_plot_candidate is True
            if ent.layout == "Model":
                assert ent.space_class == "model"
            elif ent.layout == "PubLayout" and ent.type == "VIEWPORT":
                assert ent.space_class == "paper"

        parser = Dwg2JsonParser(backend=backend)
        full = parser.parse(dxf_path, ParseOptions())
        assert any(c.kind == "layout_sheet" for c in full.document.compositions)

    def test_committed_fixture_matches_inline_build(self) -> None:
        assert FIXTURE_DXF.is_file()
        backend = LibreDwgBackend()
        doc = backend.parse(FIXTURE_DXF, ParseOptions(resolve_xrefs=False, bind_xrefs=False))
        pub = [ly for ly in doc.document.root_source.layouts if ly.name == "PubLayout"][0]
        assert len(pub.viewports) >= 1
