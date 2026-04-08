from pathlib import Path

from dwg2json.api import Dwg2JsonParser
from dwg2json.backends.base import DwgBackend
from dwg2json.models import (
    DwgJsonDocument,
    Entity,
    ParseOptions,
    ParseResult,
    ParserInfo,
    SourceDocument,
    WarningRecord,
    XrefGraphNode,
)


class FakeBackend(DwgBackend):
    name = "fake"

    def parse(self, path: Path, options: ParseOptions) -> ParseResult:
        root_id = f"src-{path.stem}"
        raw_xrefs = []
        entities = [Entity(id=f"{root_id}-e1", source_id=root_id, handle="10", type="LINE")]
        if path.name == "root.dwg":
            raw_xrefs = [{"path": "bg.dwg", "mode": "attach", "transform": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}]
        source = SourceDocument(
            id=root_id,
            path=str(path),
            resolved_path=str(path.resolve()),
            role="root",
            exists=True,
            parsed=True,
            parse_status="parsed",
            metadata={"raw_xrefs": raw_xrefs},
            entities=entities,
            warnings=[WarningRecord(code="seed", message="fake backend", source_id=root_id)],
        )
        return ParseResult(
            document=DwgJsonDocument(
                parser=ParserInfo(backend=self.name),
                root_source_id=root_id,
                sources=[source],
                xref_graph_nodes=[XrefGraphNode(source_id=root_id, path=str(path), resolved_path=str(path.resolve()), depth=0)],
            )
        )


def test_missing_xref_marks_partial(tmp_path: Path) -> None:
    root = tmp_path / "root.dwg"
    root.write_text("stub")

    parser = Dwg2JsonParser(backend=FakeBackend())
    result = parser.parse(root, ParseOptions(resolve_xrefs=True, bind_xrefs=True))

    assert result.document.completeness.status == "partial"
    assert result.document.compositions[0].completeness_status == "missing_dependencies"
    assert result.document.compositions[0].missing_source_ids
