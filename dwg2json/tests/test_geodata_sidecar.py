"""GeoData, INSUNITS, and spatial sidecar hints (research-driven GIS hooks)."""

from __future__ import annotations

from pathlib import Path

import ezdxf

from dwg2json.backends.libredwg_backend import LibreDwgBackend
from dwg2json.models import ParseOptions


class TestGeodataExtraction:
    def test_new_geodata_emitted(self, tmp_path: Path) -> None:
        p = tmp_path / "with_geo.dxf"
        doc = ezdxf.new("R2010")
        doc.modelspace().new_geodata()
        doc.saveas(str(p))

        backend = LibreDwgBackend()
        r = backend.parse(p, ParseOptions(resolve_xrefs=False, bind_xrefs=False))
        g = r.document.root_source.geodata
        assert g is not None
        assert g.coordinate_type is not None
        assert g.spatial_reference_provenance == "autodesk_geodata"
        assert r.document.root_source.metadata["backend_capabilities"]["geodata"] == "exported"

    def test_spatial_sidecar_hints(self, tmp_path: Path) -> None:
        p = tmp_path / "sidecar.dxf"
        (tmp_path / "sidecar.prj").write_text('PROJCS["fake"]', encoding="utf-8")
        ezdxf.new("R2010").saveas(str(p))

        backend = LibreDwgBackend()
        r = backend.parse(p, ParseOptions(resolve_xrefs=False, bind_xrefs=False))
        hints = r.document.root_source.metadata.get("spatial_sidecar_hints")
        assert hints is not None
        assert hints["prj_present"] is True
        assert hints["wld3_present"] is False

    def test_insunits_in_metadata(self, tmp_path: Path) -> None:
        p = tmp_path / "units.dxf"
        doc = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = 6
        doc.saveas(str(p))

        backend = LibreDwgBackend()
        r = backend.parse(p, ParseOptions(resolve_xrefs=False, bind_xrefs=False))
        assert r.document.root_source.metadata.get("insunits") == 6
