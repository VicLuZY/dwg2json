# Backends

Backends implement the `DwgBackend` abstract interface. They are responsible for format-specific DWG decoding and producing an initial `ParseResult` that the pipeline builds on.

## Interface

```python
class DwgBackend(ABC):
    name: str = "abstract"
    version: str | None = None

    @abstractmethod
    def parse(self, path: Path, options: ParseOptions) -> ParseResult:
        """Parse a DWG file and return a single-source ParseResult."""

    def parse_xref(self, path: Path, options: ParseOptions) -> ParseResult:
        """Parse an xref child DWG. Defaults to same logic as parse."""
        return self.parse(path, options)

    def is_available(self) -> bool:
        """Return True if runtime dependencies are satisfied."""
        return True
```

## Backend responsibilities

A backend must:

- Populate at least one `SourceDocument` for the root file
- Seed `xref_graph.nodes` with the root node
- Stash xref discovery results in `metadata["raw_xrefs"]` as a list of dicts with `path`, `mode`, and optional `transform` keys
- Return structured warnings rather than silently dropping unsupported data

A backend must **not**:

- Resolve xref children recursively (that's `XrefResolver`)
- Build compositions (that's `CompositionBuilder`)
- Compute confidence or completeness (those run after composition)

## Available backends

### `libredwg`

Converts DWG → DXF using LibreDWG's `dwg2dxf` CLI tool, then parses the DXF with **ezdxf**.

**Requirements:**
- `dwg2dxf` on `$PATH` (from LibreDWG)
- `ezdxf` Python package

**Extracts:**
- Document metadata (units, extents, version)
- Layers (with color, line type, frozen/locked/off states)
- Layouts (Model space and paper spaces)
- Block definitions (including xref blocks with paths)
- Entities: LINE, CIRCLE, ARC, ELLIPSE, TEXT, MTEXT, INSERT, DIMENSION, HATCH, LEADER, SPLINE, LWPOLYLINE, IMAGE, 3DSOLID, and 30+ more types
- INSERT attributes
- Type-specific geometry payloads
- 4x4 transform matrices for INSERT placements
- Raw xref declarations from xref block definitions

### `null`

Returns structurally valid but empty results. No real decoding is performed.

**Use cases:**
- Testing the pipeline without a DWG decoder
- Developing downstream tools against the JSON schema
- CI environments where LibreDWG is not installed

### `auto` (default)

Tries `libredwg` first. Falls back to `null` if `dwg2dxf` is not available.

## Selecting a backend

```python
# Auto-detect (default)
parser = Dwg2JsonParser()

# By name
parser = Dwg2JsonParser(backend="libredwg")
parser = Dwg2JsonParser(backend="null")

# By instance
from dwg2json.backends.null_backend import NullBackend
parser = Dwg2JsonParser(backend=NullBackend())
```

```bash
# CLI
dwg2json parse drawing.dwg --backend libredwg
dwg2json parse drawing.dwg --backend null
```

## Writing a custom backend

1. Subclass `DwgBackend`
2. Implement `parse()` returning a `ParseResult`
3. Seed `metadata["raw_xrefs"]` for xref discovery
4. Pass the instance to `Dwg2JsonParser(backend=my_backend)`

```python
from dwg2json.backends.base import DwgBackend
from dwg2json.models import (
    DwgJsonDocument, ParseOptions, ParseResult,
    ParserInfo, SourceDocument, XrefGraphNode,
)

class MyBackend(DwgBackend):
    name = "custom"
    version = "1.0"

    def parse(self, path, options):
        root_id = f"src-{path.stem}"
        source = SourceDocument(
            id=root_id,
            path=str(path),
            resolved_path=str(path.resolve()),
            metadata={"raw_xrefs": []},
            # ... populate layers, entities, etc.
        )
        doc = DwgJsonDocument(
            parser=ParserInfo(backend=self.name, backend_version=self.version),
            root_source_id=root_id,
            sources=[source],
        )
        doc.xref_graph.nodes.append(
            XrefGraphNode(source_id=root_id, path=str(path), depth=0)
        )
        return ParseResult(document=doc)
```
