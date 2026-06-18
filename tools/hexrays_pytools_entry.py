"""HCLI entry stub for HexRaysPyTools.

This file is the `entryPoint` referenced by `ida-plugin.json`. It ensures
the bundled `hexrays_pytools/` package is on sys.path and re-exports
`PLUGIN_ENTRY` from the package.
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent

if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from hexrays_pytools.__main__ import PLUGIN_ENTRY  # noqa: E402

__all__ = ["PLUGIN_ENTRY"]
