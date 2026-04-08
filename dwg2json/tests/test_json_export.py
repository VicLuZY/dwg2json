from pathlib import Path

from dwg2json.api import Dwg2JsonParser
from dwg2json.backends.base import DwgBackend
from dwg2json.models import DwgJsonDocument, ParseOptions, ParseResult, ParserInfo, SourceDocument, XrefGraphNode


class FakeBackend(DwgBackend):
    name = "fake"

    def parse(self, path: Path, options: ParseOptions) -> ParseResult:
        root_id = f"src-{path.stem}"
        source = SourceDocument(
            id=root_id,
            path=str(path),
            resolved_path=str(path.resolve()),
            role="root",
            exists=True,
            parsed=True,
            parse_status="parsed",
            metadata={"raw_xrefs": []},
        )
        return ParseResult(
            document=DwgJsonDocument(
                parser=ParserInfo(backend=self.name),
                root_source_id=root_id,
                sources=[source],
                xref_graph_nodes=[XrefGraphNode(source_id=root_id, path=str(path), resolved_path=str(path.resolve()), depth=0)],
            )
        )


def test_exports_single_json_file(tmp_path: Path) -> None:
    root = tmp_path / "root.dwg"
    root.write_text("stub")
    out_dir = tmp_path / "out"

    parser = Dwg2JsonParser(backend=FakeBackend())
    result = parser.parse(root, ParseOptions(out_dir=str(out_dir)))

    assert result.output_json_path is not None
    assert Path(result.output_json_path).exists()
    assert Path(result.output_json_path).name == "root.dwg.json"
