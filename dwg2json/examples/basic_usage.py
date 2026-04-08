from pathlib import Path

from dwg2json import Dwg2JsonParser, ParseOptions

parser = Dwg2JsonParser()
result = parser.parse(
    Path("sample.dwg"),
    ParseOptions(resolve_xrefs=True, bind_xrefs=True, max_xref_depth=8, out_dir="./out"),
)

result.write_json_file()
print(result.output_json_path)
print(result.document.completeness.model_dump())
