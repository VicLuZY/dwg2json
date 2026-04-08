"""Basic usage example for dwg2json."""

from pathlib import Path

from dwg2json import Dwg2JsonParser, ParseOptions

# --- Parse a DWG file ---
parser = Dwg2JsonParser()

result = parser.parse(
    Path("sample.dwg"),
    ParseOptions(
        resolve_xrefs=True,
        bind_xrefs=True,
        max_xref_depth=8,
        out_dir="./out",
    ),
)

print("Output:", result.output_json_path)
print("Completeness:", result.document.completeness.status)
print("Confidence:", result.document.interpretation_confidence.value)
print("Status:", result.document.interpretation_status)
print("Sources:", len(result.document.sources))
print("Entities:", len(result.document.all_entities))

# --- Convenience methods ---
# doc = parser.parse_file("sample.dwg")
# json_text = parser.parse_to_json_text("sample.dwg")
# output_path = parser.parse_to_json_file("sample.dwg", "sample.dwg.json")
