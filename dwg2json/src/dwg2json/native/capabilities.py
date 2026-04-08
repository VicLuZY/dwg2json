"""Backend capability introspection.

Reports which backends are available and what entity types each can extract.
"""

from __future__ import annotations

import shutil


def check_libredwg() -> dict[str, object]:
    """Check if LibreDWG CLI tools are available."""
    dwg2dxf = shutil.which("dwg2dxf")
    dwgread = shutil.which("dwgread")
    return {
        "available": dwg2dxf is not None,
        "dwg2dxf": dwg2dxf,
        "dwgread": dwgread,
    }


def check_ezdxf() -> dict[str, object]:
    """Check if ezdxf is importable."""
    try:
        import ezdxf
        return {"available": True, "version": ezdxf.__version__}
    except ImportError:
        return {"available": False, "version": None}


def report() -> dict[str, dict[str, object]]:
    """Return a capability report for all known backends."""
    return {
        "libredwg": check_libredwg(),
        "ezdxf": check_ezdxf(),
    }
