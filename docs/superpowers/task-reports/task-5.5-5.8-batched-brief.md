# Tasks 5.5-5.8 Batched: domain/actions ctree action wrappers

## Context

4 files that wrap the ctree logic from 5.1-5.4 into IDA action classes. Pattern: each action class subclasses `HexRaysPopupAction` and calls the corresponding ctree function in `activate()`.

## Files to Create (4 src + 4 test)

### 5.5 actions/recast_action.py

```python
"""RecastItemLeft/Right action wrappers."""
from __future__ import annotations
from typing import TYPE_CHECKING, Any

from ..action import HexRaysPopupAction
from ..ctree.recast import recast_item_left, recast_item_right

if TYPE_CHECKING:
    from ...session import Session


class RecastItemLeft(HexRaysPopupAction):
    description = "Recast Item (Left)"
    hotkey = "Shift+L"

    def __init__(self, session: "Session | None" = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        hx_view = self._get_hx_view(ctx)
        if hx_view and hx_view.item:
            recast_item_left(hx_view.item)

    def check(self, hx_view: Any) -> bool:
        return hx_view is not None

    @staticmethod
    def _get_hx_view(ctx: Any) -> Any:
        return getattr(ctx, "widget", None)


class RecastItemRight(HexRaysPopupAction):
    description = "Recast Item (Right)"
    hotkey = "Shift+R"

    def __init__(self, session: "Session | None" = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        hx_view = self._get_hx_view(ctx)
        if hx_view and hx_view.item:
            recast_item_right(hx_view.item)

    def check(self, hx_view: Any) -> bool:
        return hx_view is not None

    @staticmethod
    def _get_hx_view(ctx: Any) -> Any:
        return getattr(ctx, "widget", None)
```

### 5.6 actions/rename_action.py

```python
"""6 rename action wrappers."""
from __future__ import annotations
from typing import TYPE_CHECKING, Any

from ..action import HexRaysPopupAction
from ..ctree.rename import (
    rename_other, rename_inside, rename_outside,
    rename_member_from_function_name, rename_using_assert, propagate_name,
)

if TYPE_CHECKING:
    from ...session import Session


def _make_rename_action(name: str, description: str, hotkey: str, ctree_fn: Any) -> type:
    """Factory: create a rename action class wrapping a ctree function."""
    class _RenameAction(HexRaysPopupAction):
        _description = description
        _hotkey = hotkey
        _ctree_fn = staticmethod(ctree_fn)
        def __init__(self, session: "Session | None" = None) -> None:
            super().__init__(session)
        def activate(self, ctx: Any) -> None:
            hx_view = getattr(ctx, "widget", None)
            if hx_view and getattr(hx_view, "item", None):
                self._ctree_fn(hx_view.item)
        def check(self, hx_view: Any) -> bool:
            return hx_view is not None
    _RenameAction.__name__ = name
    _RenameAction.description = description
    _RenameAction.hotkey = hotkey
    return _RenameAction


# 6 rename actions. B10 fix: RenameMemberFromFunctionName uses Ctrl+Alt+N
RenameOther = _make_rename_action("RenameOther", "Take other name", "Ctrl+N", rename_other)
RenameInside = _make_rename_action("RenameInside", "Push var name into arg", "Shift+N", rename_inside)
RenameOutside = _make_rename_action("RenameOutside", "Take arg name for var", "Ctrl+Shift+N", rename_outside)
RenameMemberFromFunctionName = _make_rename_action(
    "RenameMemberFromFunctionName", "Take name from function", "Ctrl+Alt+N", rename_member_from_function_name,
)
RenameUsingAssert = _make_rename_action("RenameUsingAssert", "Rename using assert", None, rename_using_assert)
PropagateName = _make_rename_action("PropagateName", "Propagate name", "P", propagate_name)
```

### 5.7 actions/swap_if_action.py

```python
"""SwapThenElse action wrapper."""
from __future__ import annotations
from typing import TYPE_CHECKING, Any

from ..action import HexRaysPopupAction
from ..ctree.swap_if import swap_if_then_else

if TYPE_CHECKING:
    from ...session import Session


class SwapThenElse(HexRaysPopupAction):
    description = "Swap if/then/else branches"
    hotkey = "Shift+Alt+S"

    def __init__(self, session: "Session | None" = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        hx_view = getattr(ctx, "widget", None)
        if hx_view:
            swap_if_then_else(hx_view)

    def check(self, hx_view: Any) -> bool:
        return hx_view is not None
```

### 5.8 actions/containing_structure.py

```python
"""SelectContainingStructure / ResetContainingStructure action wrappers."""
from __future__ import annotations
from typing import TYPE_CHECKING, Any

from ..action import HexRaysPopupAction
from ..ctree.negative_offsets import (
    select_containing_structure, reset_containing_structure,
)

if TYPE_CHECKING:
    from ...session import Session


class SelectContainingStructure(HexRaysPopupAction):
    description = "Select Containing Structure"

    def __init__(self, session: "Session | None" = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        hx_view = getattr(ctx, "widget", None)
        if hx_view and getattr(hx_view, "item", None):
            select_containing_structure(hx_view.item)

    def check(self, hx_view: Any) -> bool:
        return hx_view is not None


class ResetContainingStructure(HexRaysPopupAction):
    description = "Reset Containing Structure"

    def __init__(self, session: "Session | None" = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        hx_view = getattr(ctx, "widget", None)
        if hx_view and getattr(hx_view, "item", None):
            reset_containing_structure(hx_view.item)

    def check(self, hx_view: Any) -> bool:
        return hx_view is not None
```

## Tests (8 test files)

`tests/domain/actions/test_recast_action.py`:

```python
"""Test RecastItemLeft/Right actions."""
from hexrays_pytools.domain.actions.recast_action import RecastItemLeft, RecastItemRight


def test_recast_left_init() -> None:
    a = RecastItemLeft()
    assert a.hotkey == "Shift+L"


def test_recast_left_check() -> None:
    a = RecastItemLeft()
    assert a.check(None) is False
    assert a.check(MagicMock()) is True


def test_recast_right_init() -> None:
    a = RecastItemRight()
    assert a.hotkey == "Shift+R"
```

`tests/domain/actions/test_rename_action.py`:

```python
"""Test 6 rename actions."""
from hexrays_pytools.domain.actions.rename_action import (
    RenameOther, RenameInside, RenameOutside,
    RenameMemberFromFunctionName, RenameUsingAssert, PropagateName,
)


def test_all_rename_classes_exist() -> None:
    """All 6 rename action classes are importable."""
    for cls in (RenameOther, RenameInside, RenameOutside,
                RenameMemberFromFunctionName, RenameUsingAssert, PropagateName):
        assert cls is not None


def test_b10_hotkey_collision_fix() -> None:
    """RenameMemberFromFunctionName uses Ctrl+Alt+N (B10 fix)."""
    assert RenameMemberFromFunctionName.hotkey == "Ctrl+Alt+N"
    assert RenameOther.hotkey == "Ctrl+N"
    assert RenameMemberFromFunctionName.hotkey != RenameOther.hotkey


def test_all_rename_can_instantiate() -> None:
    for cls in (RenameOther, RenameInside, RenameOutside,
                RenameMemberFromFunctionName, RenameUsingAssert, PropagateName):
        action = cls()
        assert action is not None
```

`tests/domain/actions/test_swap_if_action.py`:

```python
"""Test SwapThenElse action."""
from hexrays_pytools.domain.actions.swap_if_action import SwapThenElse


def test_swap_then_else_init() -> None:
    a = SwapThenElse()
    assert a.hotkey == "Shift+Alt+S"


def test_swap_then_else_check() -> None:
    a = SwapThenElse()
    assert a.check(MagicMock()) is True
```

`tests/domain/actions/test_containing_structure.py`:

```python
"""Test SelectContainingStructure/ResetContainingStructure actions."""
from hexrays_pytools.domain.actions.containing_structure import (
    SelectContainingStructure, ResetContainingStructure,
)


def test_select_containing_init() -> None:
    a = SelectContainingStructure()
    assert a.description == "Select Containing Structure"


def test_reset_containing_init() -> None:
    a = ResetContainingStructure()
    assert a.description == "Reset Containing Structure"


def test_both_can_instantiate() -> None:
    SelectContainingStructure()
    ResetContainingStructure()
```

## Verification

```bash
PYTHONPATH=src pytest tests/domain/actions/ -v
python -m mypy --strict src/hexrays_pytools/domain/actions/
python -m ruff check src/hexrays_pytools/domain/actions/ tests/domain/actions/
PYTHONPATH=src pytest  # full suite
```

## Commits (4 separate for clean history)

```bash
git add src/hexrays_pytools/domain/actions/recast_action.py tests/domain/actions/test_recast_action.py
git commit -m "feat(actions): add RecastItemLeft/Right action wrappers"

git add src/hexrays_pytools/domain/actions/rename_action.py tests/domain/actions/test_rename_action.py
git commit -m "feat(actions): add 6 rename action wrappers (B10 verified)"

git add src/hexrays_pytools/domain/actions/swap_if_action.py tests/domain/actions/test_swap_if_action.py
git commit -m "feat(actions): add SwapThenElse action wrapper"

git add src/hexrays_pytools/domain/actions/containing_structure.py tests/domain/actions/test_containing_structure.py
git commit -m "feat(actions): add Select/ResetContainingStructure wrappers"
```

## Report

Write 4 separate reports at:
- `D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-5.5-report.md`
- `D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-5.6-report.md`
- `D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-5.7-report.md`
- `D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-5.8-report.md`

After all 4 tasks, return:
- 4 commit SHAs + subjects
- Test summary
- 4 report paths