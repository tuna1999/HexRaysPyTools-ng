# Task 1.4 Brief: domain/settings.py

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\settings.py`
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\test_settings.py`

## Required Content (verbatim)

### `src/hexrays_pytools/domain/settings.py`

```python
"""HCLI settings wrapper.

Reads settings stored by the HCLI plugin installer into `ida_settings`,
mapping them onto the Session dataclass. Replaces the original `.cfg` file
parser in `settings.py`.
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

import ida_settings  # type: ignore[import-not-found]

if TYPE_CHECKING:
    from .session import Session

logger = logging.getLogger(__name__)

SETTING_KEYS: tuple[str, ...] = (
    "log_level",
    "propagate_through_all_names",
    "store_xrefs",
    "scan_any_type",
    "templated_types_file",
)


def load_into(session: "Session") -> None:
    """Read HCLI settings into session fields.

    Each setting that returns a value is applied; None values are skipped
    (the user did not configure that setting in HCLI).
    """
    for key in SETTING_KEYS:
        try:
            raw = ida_settings.get_current_plugin_setting(key)
        except Exception as e:  # noqa: BLE001 — HCLI may not be initialized
            logger.debug("ida_settings not available for %s: %s", key, e)
            continue
        if raw is None:
            continue
        _apply(session, key, raw)


def _apply(session: "Session", key: str, raw: object) -> None:
    match key:
        case "log_level":
            session.log_level = getattr(logging, str(raw).upper(), logging.INFO)
        case "propagate_through_all_names":
            session.propagate_through_all_names = bool(raw)
        case "store_xrefs":
            session.store_xrefs = bool(raw)
        case "scan_any_type":
            session.scan_any_type = bool(raw)
        case "templated_types_file":
            session.templated_types_file = str(raw)
        case _:
            logger.debug("Unknown setting key: %s", key)
```

### `tests/domain/test_settings.py`

```python
"""Test settings.load_into."""
from hexrays_pytools.domain.session import Session
from hexrays_pytools.domain.settings import load_into, SETTING_KEYS


def test_setting_keys_listed() -> None:
    """SETTING_KEYS contains the 5 expected keys."""
    assert "log_level" in SETTING_KEYS
    assert "propagate_through_all_names" in SETTING_KEYS
    assert "store_xrefs" in SETTING_KEYS
    assert "scan_any_type" in SETTING_KEYS
    assert "templated_types_file" in SETTING_KEYS


def test_load_into_applies_log_level() -> None:
    """load_into maps the 'log_level' string setting to a logging constant."""
    import logging
    ida_settings = __import__("ida_settings")
    ida_settings.get_current_plugin_setting.side_effect = lambda k: "DEBUG" if k == "log_level" else None
    s = Session()
    load_into(s)
    assert s.log_level == logging.DEBUG


def test_load_into_applies_bool_settings() -> None:
    """load_into maps 'store_xrefs' and 'propagate_through_all_names' to booleans."""
    ida_settings = __import__("ida_settings")
    def fake(k: str) -> object:
        return {"store_xrefs": True, "propagate_through_all_names": True}.get(k)
    ida_settings.get_current_plugin_setting.side_effect = fake
    s = Session()
    load_into(s)
    assert s.store_xrefs is True
    assert s.propagate_through_all_names is True


def test_load_into_skips_none_values() -> None:
    """load_into leaves default values when HCLI returns None."""
    ida_settings = __import__("ida_settings")
    ida_settings.get_current_plugin_setting.return_value = None
    s = Session()
    s.store_xrefs = True  # set non-default
    load_into(s)
    # None is skipped, so default is preserved
    assert s.store_xrefs is True


def test_load_into_handles_ida_settings_exception() -> None:
    """load_into catches exceptions from ida_settings (e.g. in tests)."""
    ida_settings = __import__("ida_settings")
    ida_settings.get_current_plugin_setting.side_effect = RuntimeError("not initialized")
    s = Session()
    load_into(s)  # should not raise
    assert s.log_level == 20  # default INFO
```

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/test_settings.py -v
python -m mypy --strict src/hexrays_pytools/domain/settings.py
python -m ruff check src/hexrays_pytools/domain/settings.py tests/domain/test_settings.py
```

## Commit

```bash
git add src/hexrays_pytools/domain/settings.py tests/domain/test_settings.py
git commit -m "feat(domain): add settings wrapper (ida_settings HCLI integration)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-1.4-report.md`

Apply minimal lint fixes as needed. Document any deviations in DONE_WITH_CONCERNS.