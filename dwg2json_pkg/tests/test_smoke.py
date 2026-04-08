from dwg2json import Dwg2JsonParser


def test_seed_parser_smoke(tmp_path):
    src = tmp_path / "test.dwg"
    src.write_bytes(b"placeholder")
    parser = Dwg2JsonParser()
    doc = parser.parse_file(str(src))
    assert doc.package_name == "dwg2json"
    assert doc.root_document_id == "test"
