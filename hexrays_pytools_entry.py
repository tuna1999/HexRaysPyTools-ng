"""HCLI entry for HexRaysPyTools.

Referenced by `ida-plugin.json`'s `entryPoint` (relative to the plugin root).
IDA/HCLI expects `PLUGIN_ENTRY` (a callable returning a `plugin_t` instance)
in this file.

Dual-mode path resolution so the *same* file works in two layouts:

  - **Release ZIP (flat):** ``hexrays_pytools_entry.py`` and the
    ``hexrays_pytools/`` package sit side-by-side at the plugin root.
  - **Dev checkout (src-layout):** this entry file sits at the repo root,
    while the package lives under ``src/hexrays_pytools/``. This is the
    layout used when symlinking/junctioning the repo directly into
    ``$IDAUSR/plugins/HexRaysPyTools/`` for live debugging.
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent

# Release layout: package sits next to this entry file.
_flat_pkg = _HERE / "hexrays_pytools"
# Dev layout (src-layout): package sits under src/.
_src_pkg = _HERE / "src" / "hexrays_pytools"

if _src_pkg.is_dir():
    _pkg_parent = _HERE / "src"
elif _flat_pkg.is_dir():
    _pkg_parent = _HERE
else:
    raise ImportError(
        "hexrays_pytools package not found. Expected either "
        f"{_flat_pkg} (release layout) or {_src_pkg} (src layout) to exist."
    )

_pkg_parent_str = str(_pkg_parent)
if _pkg_parent_str not in sys.path:
    sys.path.insert(0, _pkg_parent_str)

from hexrays_pytools.__main__ import PLUGIN_ENTRY  # noqa: E402  # type: ignore[import-untyped]

__all__ = ["PLUGIN_ENTRY"]
