# Installation

## Python package

Requires **Python 3.11+**.

```bash
pip install dwg2json
```

This installs the core package with its Python dependencies (pydantic, orjson, typer, rich, ezdxf).

### Dev dependencies

For development, install with the `dev` extra:

```bash
pip install -e ".[dev]"
```

This adds pytest, pytest-cov, ruff, mypy, and jsonschema.

## System dependency: LibreDWG

The primary backend converts DWG files to DXF using **LibreDWG**'s `dwg2dxf` tool, then parses the DXF with **ezdxf**. LibreDWG is a system-level dependency — it must be installed separately.

### Ubuntu / Debian

```bash
sudo apt install libredwg-utils
```

### macOS (Homebrew)

```bash
brew install libredwg
```

### From source

```bash
git clone https://github.com/LibreDWG/libredwg.git
cd libredwg
mkdir build && cd build
cmake ..
make -j$(nproc)
sudo make install
```

### Verification

After installing, verify `dwg2dxf` is on your `PATH`:

```bash
which dwg2dxf
dwg2dxf --version
```

## Without LibreDWG

If LibreDWG is not installed, the default `auto` backend falls back to the **null** backend. The null backend produces structurally valid but empty results — useful for testing the pipeline, developing downstream tools, and validating JSON schema compliance without a real decoder.

You can also select backends explicitly:

```python
from dwg2json import Dwg2JsonParser

parser = Dwg2JsonParser(backend="null")   # always null
parser = Dwg2JsonParser(backend="libredwg")  # requires dwg2dxf
parser = Dwg2JsonParser(backend="auto")   # default: try libredwg, fall back to null
```

Or via CLI:

```bash
dwg2json parse drawing.dwg --backend null --out ./out
```
