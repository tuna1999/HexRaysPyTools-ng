# Task 1.6 Brief: Plugin entry (plugin.py, __main__.py, entry stub)

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\plugin.py`
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\__main__.py`
3. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tools\hexrays_pytools_entry.py`

## Required Content (verbatim)

### `src/hexrays_pytools/plugin.py`

```python
"""IDA plugin entry point.

Defines `HexRaysPyToolsPlugin` (idaapi.plugin_t subclass) that manages the
plugin lifecycle: init/run/term. All state lives in class attributes (per
plugin instance, not module global).
"""
from __future__ import annotations
import logging

import idaapi  # type: ignore[import-not-found]

from .session import Session

logger = logging.getLogger(__name__)


class HexRaysPyToolsPlugin(idaapi.plugin_t):
    """The HexRaysPyTools IDA plugin."""

    flags: int = 0
    comment: str = "Comprehensive toolkit for Hex-Rays decompiler"
    help: str = "See https://github.com/yourname/HexRaysPyTools"
    wanted_name: str = "HexRaysPyTools"
    wanted_hotkey: str = ""

    # Per-instance state (not module-level globals)
    session: Session | None = None

    @classmethod
    def init(cls) -> int:
        """Initialize plugin: open session, return PLUGIN_KEEP."""
        if not idaapi.init_hexrays_plugin():
            logger.error("Failed to initialize Hex-Rays SDK")
            return idaapi.PLUGIN_SKIP

        cls.session = Session()
        cls.session.open()
        # ActionRegistry and HxCallbackRegistry will be wired in Phase 4
        logger.info("HexRaysPyTools plugin initialized")
        return idaapi.PLUGIN_KEEP

    @classmethod
    def run(cls, *args) -> None:
        """Run the plugin (no-op — actions handle their own execution)."""
        pass

    @classmethod
    def term(cls) -> None:
        """Terminate plugin: close session."""
        if cls.session:
            cls.session.close()
            cls.session = None
        idaapi.term_hexrays_plugin()
        logger.info("HexRaysPyTools plugin terminated")
```

### `src/hexrays_pytools/__main__.py`

```python
"""HexRaysPyTools main entry — exports PLUGIN_ENTRY for IDA.

HCLI/IDA expects `PLUGIN_ENTRY` (or a callable returning a plugin_t instance)
in the entry file referenced by `ida-plugin.json`'s `entryPoint`.
"""
from .plugin import HexRaysPyToolsPlugin

PLUGIN_ENTRY = HexRaysPyToolsPlugin
```

### `tools/hexrays_pytools_entry.py`

```python
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
```

## Tests

This task has no tests of its own. The plugin entry is exercised manually in IDA.
Verify by:

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src python -c "from hexrays_pytools.__main__ import PLUGIN_ENTRY; print(PLUGIN_ENTRY)"
# Expected: <class 'hexrays_pytools.plugin.HexRaysPyToolsPlugin'>

python -m mypy --strict src/hexrays_pytools/plugin.py src/hexrays_pytools/__main__.py tools/hexrays_pytools_entry.py
python -m ruff check src/hexrays_pytools/plugin.py src/hexrays_pytools/__main__.py tools/hexrays_pytools_entry.py
```

## Commit

```bash
git add src/hexrays_pytools/plugin.py src/hexrays_pytools/__main__.py tools/hexrays_pytools_entry.py
git commit -m "feat(plugin): add PLUGIN_ENTRY and HCLI stub (Phase 1 wiring)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-1.6-report.md`

Apply minimal lint fixes as needed. Document any deviations in DONE_WITH_CONCERNS.
