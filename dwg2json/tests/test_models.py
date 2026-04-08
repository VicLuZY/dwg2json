"""Unit tests for canonical data models."""

from dwg2json.models import (
    BlockDefinition,
    BoundingBox,
    CompletenessReport,
    Composition,
    DwgJsonDocument,
    Entity,
    InterpretationConfidence,
    Layer,
    Layout,
    MissingReference,
    ParseOptions,
    ParseResult,
    ParserInfo,
    Point3D,
    SourceDocument,
    WarningRecord,
    XrefBindingMetadata,
    XrefGraph,
    XrefGraphEdge,
    XrefGraphNode,
)


class TestBoundingBox:
    def test_defaults(self) -> None:
        bb = BoundingBox(min_x=0, min_y=0, max_x=10, max_y=10)
        assert bb.min_z == 0.0
        assert bb.max_z == 0.0

    def test_all_fields(self) -> None:
        bb = BoundingBox(min_x=1, min_y=2, min_z=3, max_x=4, max_y=5, max_z=6)
        assert bb.model_dump() == {
            "min_x": 1,
            "min_y": 2,
            "min_z": 3,
            "max_x": 4,
            "max_y": 5,
            "max_z": 6,
        }


class TestParserInfo:
    def test_defaults(self) -> None:
        pi = ParserInfo(backend="null")
        assert pi.name == "dwg2json"
        assert pi.version == "0.1.0"
        assert pi.backend == "null"
        assert pi.timestamp  # auto-generated


class TestWarningRecord:
    def test_minimal(self) -> None:
        w = WarningRecord(code="test", message="hello")
        assert w.severity == "warning"
        assert w.source_id is None


class TestLayer:
    def test_defaults(self) -> None:
        la = Layer(id="l1", name="0")
        assert not la.is_frozen
        assert not la.is_locked
        assert not la.is_off
        assert la.color_index is None


class TestLayout:
    def test_model_space(self) -> None:
        lay = Layout(id="layout-model", name="Model", is_model_space=True)
        assert lay.is_model_space


class TestBlockDefinition:
    def test_xref_block(self) -> None:
        blk = BlockDefinition(id="b1", name="BG", is_xref=True, xref_path="bg.dwg")
        assert blk.is_xref
        assert blk.xref_path == "bg.dwg"


class TestEntity:
    def test_minimal(self) -> None:
        e = Entity(id="e1", source_id="s1", handle="10", type="LINE")
        assert e.is_visible
        assert e.text is None
        assert e.geometry == {}
        assert e.attributes == {}

    def test_text_entity(self) -> None:
        e = Entity(id="e2", source_id="s1", handle="20", type="TEXT", text="Hello")
        assert e.text == "Hello"

    def test_insert_entity(self) -> None:
        e = Entity(
            id="e3", source_id="s1", handle="30", type="INSERT",
            block_name="DOOR",
            insert_point=Point3D(x=5, y=10, z=0),
            scale=Point3D(x=1, y=1, z=1),
            rotation=45.0,
            attributes={"TAG": "D01"},
        )
        assert e.block_name == "DOOR"
        assert e.insert_point.x == 5
        assert e.rotation == 45.0
        assert e.attributes["TAG"] == "D01"


class TestXrefBindingMetadata:
    def test_missing(self) -> None:
        xb = XrefBindingMetadata(
            saved_path="bg.dwg",
            exists=False,
            parsed=False,
            missing_reason="not found",
        )
        assert not xb.exists
        assert xb.missing_reason == "not found"


class TestSourceDocument:
    def test_root(self) -> None:
        sd = SourceDocument(id="s1", path="root.dwg", role="root")
        assert sd.exists
        assert sd.parsed
        assert sd.parse_status == "parsed"

    def test_missing_xref(self) -> None:
        sd = SourceDocument(
            id="s2", path="bg.dwg", role="xref",
            exists=False, parsed=False, parse_status="missing",
        )
        assert not sd.exists
        assert sd.parse_status == "missing"


class TestXrefGraph:
    def test_empty(self) -> None:
        g = XrefGraph()
        assert g.nodes == []
        assert g.edges == []

    def test_with_nodes_and_edges(self) -> None:
        g = XrefGraph(
            nodes=[XrefGraphNode(source_id="s1", path="root.dwg")],
            edges=[XrefGraphEdge(host_source_id="s1", target_source_id="s2")],
        )
        assert len(g.nodes) == 1
        assert len(g.edges) == 1


class TestComposition:
    def test_complete(self) -> None:
        c = Composition(id="c1", name="test", root_source_id="s1")
        assert c.completeness_status == "complete"
        assert c.missing_source_ids == []

    def test_missing_deps(self) -> None:
        c = Composition(
            id="c1", name="test", root_source_id="s1",
            completeness_status="missing_dependencies",
            missing_source_ids=["s2"],
        )
        assert c.completeness_status == "missing_dependencies"


class TestInterpretationConfidence:
    def test_default(self) -> None:
        ic = InterpretationConfidence()
        assert ic.value == 1.0
        assert ic.factors == []

    def test_apply_penalty(self) -> None:
        ic = InterpretationConfidence()
        ic.apply_penalty("missing_xref", 0.15, "bg.dwg missing")
        assert ic.value == 0.85
        assert len(ic.factors) == 1

    def test_recompute(self) -> None:
        ic = InterpretationConfidence()
        ic.apply_penalty("a", 0.1)
        ic.apply_penalty("b", 0.2)
        ic.recompute()
        assert abs(ic.value - 0.7) < 0.01
        assert ic.explanation is not None

    def test_floor_at_zero(self) -> None:
        ic = InterpretationConfidence()
        ic.apply_penalty("catastrophe", 2.0)
        assert ic.value == 0.0


class TestCompletenessReport:
    def test_complete(self) -> None:
        doc = DwgJsonDocument(
            parser=ParserInfo(backend="null"),
            root_source_id="s1",
            sources=[SourceDocument(id="s1", path="root.dwg", role="root")],
        )
        cr = CompletenessReport()
        cr.recompute_from_document(doc)
        assert cr.status == "complete"
        assert cr.consumer_caution is None

    def test_partial_with_missing_xref(self) -> None:
        doc = DwgJsonDocument(
            parser=ParserInfo(backend="null"),
            root_source_id="s1",
            sources=[
                SourceDocument(id="s1", path="root.dwg", role="root"),
                SourceDocument(
                    id="s2",
                    path="bg.dwg",
                    role="xref",
                    exists=False,
                    parsed=False,
                    parse_status="missing",
                ),
            ],
        )
        cr = CompletenessReport()
        cr.recompute_from_document(doc)
        assert cr.status == "partial"
        assert cr.missing_xrefs_count == 1
        assert cr.consumer_caution is not None


class TestMissingReference:
    def test_defaults(self) -> None:
        mr = MissingReference(requested_path="bg.dwg", parent_document_id="s1")
        assert mr.kind == "xref"
        assert mr.severity == "high"
        assert mr.interpretation_impacted


class TestDwgJsonDocument:
    def test_root_source_property(self) -> None:
        doc = DwgJsonDocument(
            parser=ParserInfo(backend="null"),
            root_source_id="s1",
            sources=[SourceDocument(id="s1", path="root.dwg")],
        )
        assert doc.root_source.id == "s1"

    def test_root_source_missing_raises(self) -> None:
        doc = DwgJsonDocument(
            parser=ParserInfo(backend="null"),
            root_source_id="missing",
            sources=[SourceDocument(id="s1", path="root.dwg")],
        )
        import pytest
        with pytest.raises(KeyError):
            _ = doc.root_source

    def test_all_entities(self) -> None:
        doc = DwgJsonDocument(
            parser=ParserInfo(backend="null"),
            root_source_id="s1",
            sources=[
                SourceDocument(
                    id="s1", path="root.dwg",
                    entities=[Entity(id="e1", source_id="s1", handle="10", type="LINE")],
                ),
                SourceDocument(
                    id="s2", path="bg.dwg", role="xref",
                    entities=[Entity(id="e2", source_id="s2", handle="20", type="CIRCLE")],
                ),
            ],
        )
        assert len(doc.all_entities) == 2

    def test_derive_interpretation_status(self) -> None:
        doc = DwgJsonDocument(
            parser=ParserInfo(backend="null"),
            root_source_id="s1",
            sources=[SourceDocument(id="s1", path="root.dwg")],
        )
        assert doc.derive_interpretation_status() == "complete"

    def test_serialisation_roundtrip(self) -> None:
        doc = DwgJsonDocument(
            parser=ParserInfo(backend="null"),
            root_source_id="s1",
            sources=[SourceDocument(id="s1", path="root.dwg")],
        )
        data = doc.model_dump(mode="json")
        doc2 = DwgJsonDocument.model_validate(data)
        assert doc2.root_source_id == "s1"
        assert doc2.schema_version == "0.1.0"


class TestParseOptions:
    def test_defaults(self) -> None:
        opts = ParseOptions()
        assert opts.resolve_xrefs is True
        assert opts.bind_xrefs is True
        assert opts.max_xref_depth == 8
        assert opts.missing_xref_policy == "record"
        assert opts.xref_search_roots == []
        assert opts.indent == 2


class TestParseResult:
    def test_source_path(self) -> None:
        doc = DwgJsonDocument(
            parser=ParserInfo(backend="null"),
            root_source_id="s1",
            sources=[SourceDocument(id="s1", path="/tmp/root.dwg")],
        )
        pr = ParseResult(document=doc)
        assert str(pr.source_path) == "/tmp/root.dwg"
