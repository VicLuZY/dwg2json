"""Native bridge placeholder.

This module will host Rust/C++/C bindings (via PyO3, pybind11, cffi,
or ctypes) once a native DWG decoding core is implemented.

Current backend strategy uses LibreDWG CLI tools as a subprocess
bridge with ezdxf for DXF parsing.  A future native bridge will
replace the subprocess hop for performance.
"""

from __future__ import annotations


class NativeBridge:
    """Placeholder for a future native decoding bridge."""

    @staticmethod
    def is_available() -> bool:
        return False

    @staticmethod
    def decode(path: str) -> dict:
        raise NotImplementedError(
            "No native bridge is compiled. Use the LibreDWG subprocess backend."
        )
