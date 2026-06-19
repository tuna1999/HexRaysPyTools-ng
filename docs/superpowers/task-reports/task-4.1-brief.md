# Task 4.1 Brief: domain/actions/action.py

## Files (2)
1. `src/hexrays_pytools/domain/actions/__init__.py` (empty)
2. `src/hexrays_pytools/domain/actions/action.py`
3. `tests/domain/actions/__init__.py` (empty)
4. `tests/domain/actions/test_action.py`

## `action.py` (verbatim)

```python
"""Base classes for actions (right-click menu + hotkey)."""
from __future__ import annotations
from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

if TYPE_CHECKING:
    from ..session import Session


class Action(idaapi.action_handler_t):  # type: ignore[misc]
    """Base class for all actions."""

    description: str = ""
    hotkey: str | None = None

    def __init__(self, session: "Session | None" = None) -> None:
        super().__init__()
        self._session = session

    @property
    def name(self) -> str:
        return f"HexRaysPyTools:{type(self).__name__}"

    def activate(self, ctx: Any) -> None:  # noqa: D401 - IDA SWIG override
        raise NotImplementedError

    def update(self, ctx: Any) -> int:  # noqa: D401 - IDA SWIG override
        return int(idaapi.AST_DISABLE_FOR_WIDGET)


class HexRaysPopupAction(Action):
    """Action attached to right-click menu in pseudocode."""

    def check(self, hx_view: Any) -> bool:
        raise NotImplementedError

    def update(self, ctx: Any) -> int:
        if ctx.widget_type == idaapi.BWN_PSEUDOCODE:
            return int(idaapi.AST_ENABLE_FOR_WIDGET)
        return int(idaapi.AST_DISABLE_FOR_WIDGET)


class HexRaysXrefAction(Action):
    """Action also enabled in Local Types view (BWN_TILIST)."""

    def check(self, hx_view: Any) -> bool:
        raise NotImplementedError

    def update(self, ctx: Any) -> int:
        if ctx.widget_type in (idaapi.BWN_PSEUDOCODE, idaapi.BWN_TILIST):
            return int(idaapi.AST_ENABLE_FOR_WIDGET)
        return int(idaapi.AST_DISABLE_FOR_WIDGET)


class HexRaysPopupRequestHandler:
    """Wraps HexRaysPopupAction for the hxe_populating_popup event."""

    def __init__(self, action: HexRaysPopupAction) -> None:
        self._action = action

    def handle(self, event: int, *args: Any) -> None:
        form, popup, hx_view = args
        if self._action.check(hx_view):
            idaapi.attach_action_to_popup(form, popup, self._action.name, None)
```

## `test_action.py` (verbatim)

```python
"""Test Action base classes."""
import pytest
from hexrays_pytools.domain.actions.action import (
    Action, HexRaysPopupAction, HexRaysXrefAction, HexRaysPopupRequestHandler,
)


def test_action_name_uses_class_name() -> None:
    a = Action()
    assert a.name == "HexRaysPyTools:Action"


def test_action_init_accepts_session() -> None:
    session = MagicMock()
    a = Action(session=session)
    assert a._session is session


def test_action_activate_raises_not_implemented() -> None:
    a = Action()
    with pytest.raises(NotImplementedError):
        a.activate(None)


def test_hexrays_popup_action_check_raises() -> None:
    a = HexRaysPopupAction()
    with pytest.raises(NotImplementedError):
        a.check(None)


def test_hexrays_xref_action_check_raises() -> None:
    a = HexRaysXrefAction()
    with pytest.raises(NotImplementedError):
        a.check(None)


def test_popup_request_handler_calls_attach_when_check_passes() -> None:
    """Request handler attaches action to popup when check returns True."""
    idaapi = __import__("idaapi")
    action = MagicMock()
    action.check.return_value = True
    action.name = "test_action"
    handler = HexRaysPopupRequestHandler(action)
    form = MagicMock()
    popup = MagicMock()
    hx_view = MagicMock()
    handler.handle(0, form, popup, hx_view)
    idaapi.attach_action_to_popup.assert_called_once_with(form, popup, "test_action", None)


def test_popup_request_handler_skips_when_check_fails() -> None:
    idaapi = __import__("idaapi")
    action = MagicMock()
    action.check.return_value = False
    handler = HexRaysPopupRequestHandler(action)
    handler.handle(0, MagicMock(), MagicMock(), MagicMock())
    idaapi.attach_action_to_popup.assert_not_called()
```

Add `from unittest.mock import MagicMock` to imports.

## Verification
```bash
PYTHONPATH=src pytest tests/domain/actions/test_action.py -v
python -m mypy --strict src/hexrays_pytools/domain/actions/action.py
python -m ruff check src/hexrays_pytools/domain/actions/action.py tests/domain/actions/test_action.py
```

## Commit
```bash
git add src/hexrays_pytools/domain/actions/ tests/domain/actions/
git commit -m "feat(actions): add Action base classes (with session injection)"
```

## Report
`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-4.1-report.md`