# Tasks 4.3 + 4.4 + 4.5 Batched Brief

## Context

Three remaining Phase 4 tasks bundled for efficiency:
- 4.3: hx_callback.py (HxCallbackManager for hxe_* events)
- 4.4: hx_events.py (4 event handlers)
- 4.5: 8 action files (form_requests, function_signature, scanners, struct_xref, struct_creation, structs_by_size, guess_allocation, member_double_click, virtual_table, swap_if_action, recast_action, rename_action, containing_structure)

The action classes are mostly stubs (placeholder logic); the goal is to register them so the ActionRegistry doesn't fail. Real behavior comes from real IDA + plugin refactors.

## Files to Create

### 4.3 hx_callback.py (1 file + 1 test)

`src/hexrays_pytools/domain/actions/hx_callback.py`:

```python
"""Manage hxe_* (Hex-Rays decompiler) callbacks."""
from __future__ import annotations
import logging
from collections import defaultdict
from typing import Any, Callable

import idaapi  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


class HxCallbackManager:
    """Installs/removes a Hex-Rays callback dispatcher."""

    def __init__(self) -> None:
        self._handlers: dict = defaultdict(list)
        self._installed = False

    def install(self) -> None:
        if self._installed:
            return
        idaapi.install_hexrays_callback(self._dispatch)
        self._installed = True

    def register(self, event_id: int, handler: Any) -> None:
        """Register a handler for `event_id`."""
        self._handlers[event_id].append(handler)

    def _dispatch(self, event: int, *args: Any) -> int:
        for handler in self._handlers.get(event, []):
            try:
                handler.handle(event, *args)
            except Exception as e:  # noqa: BLE001
                logger.exception("HxCallback handler failed: %s", e)
        return 0

    def detach_all(self) -> None:
        if self._installed:
            idaapi.remove_hexrays_callback(self._dispatch)
            self._installed = False
        self._handlers.clear()
```

`tests/domain/actions/test_hx_callback.py`:

```python
"""Test HxCallbackManager."""
from hexrays_pytools.domain.actions.hx_callback import HxCallbackManager


def test_init_empty() -> None:
    m = HxCallbackManager()
    assert m._installed is False
    assert m._handlers == {}


def test_register_adds_handler() -> None:
    m = HxCallbackManager()
    handler = MagicMock()
    m.register(idaapi.hxe_maturity, handler)
    assert handler in m._handlers[idaapi.hxe_maturity]


def test_install_calls_idaapi() -> None:
    """install() calls install_hexrays_callback once."""
    idaapi = __import__("idaapi")
    idaapi.install_hexrays_callback.reset_mock()
    m = HxCallbackManager()
    m.install()
    idaapi.install_hexrays_callback.assert_called_once()
    assert m._installed is True


def test_install_idempotent() -> None:
    """install() called twice doesn't re-install."""
    m = HxCallbackManager()
    m.install()
    m.install()  # second call no-op
    idaapi = __import__("idaapi")
    assert idaapi.install_hexrays_callback.call_count == 1


def test_dispatch_invokes_handlers() -> None:
    m = HxCallbackManager()
    handler = MagicMock()
    m.register(idaapi.hxe_maturity, handler)
    m._dispatch(idaapi.hxe_maturity, "arg1")
    handler.handle.assert_called_once_with(idaapi.hxe_maturity, "arg1")


def test_dispatch_handles_exceptions() -> None:
    """Exceptions in one handler don't break other handlers."""
    m = HxCallbackManager()
    bad = MagicMock()
    bad.handle.side_effect = RuntimeError("boom")
    good = MagicMock()
    m.register(idaapi.hxe_maturity, bad)
    m.register(idaapi.hxe_maturity, good)
    m._dispatch(idaapi.hxe_maturity)
    good.handle.assert_called_once()


def test_detach_all_clears() -> None:
    m = HxCallbackManager()
    m.register(idaapi.hxe_maturity, MagicMock())
    m.detach_all()
    assert m._handlers == {}
    assert m._installed is False
```

### 4.4 hx_events.py (1 file + 1 test)

`src/hexrays_pytools/domain/actions/hx_events.py`:

```python
"""4 event handlers: MemberDoubleClick, PotentialNegativeCollector, StructXrefCollector, SilentIfSwapper."""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..session import Session

logger = logging.getLogger(__name__)


class MemberDoubleClick:
    """Handle hxe_double_click — navigate to virtual function."""

    def __init__(self, session: "Session | None" = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        # Real implementation requires UI navigation; stub for now
        logger.debug("MemberDoubleClick.handle: event=%d", event)


class PotentialNegativeCollector:
    """Run at CMAT_BUILT — detect CONTAINING_RECORD patterns."""

    def __init__(self, session: "Session | None" = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        logger.debug("PotentialNegativeCollector.handle")


class StructXrefCollector:
    """Run at CMAT_FINAL — populate XrefStorage."""

    def __init__(self, session: "Session | None" = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        logger.debug("StructXrefCollector.handle")


class SilentIfSwapper:
    """Run at CMAT_TRANS1+2 — re-apply saved if-swaps."""

    def __init__(self, session: "Session | None" = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        logger.debug("SilentIfSwapper.handle")
```

`tests/domain/actions/test_hx_events.py`:

```python
"""Test 4 event handlers."""
from hexrays_pytools.domain.actions.hx_events import (
    MemberDoubleClick, PotentialNegativeCollector, StructXrefCollector, SilentIfSwapper,
)


def test_member_double_click_handle() -> None:
    h = MemberDoubleClick()
    h.handle(0)  # should not raise


def test_potential_negative_collector_handle() -> None:
    h = PotentialNegativeCollector()
    h.handle(0)


def test_struct_xref_collector_handle() -> None:
    h = StructXrefCollector()
    h.handle(0)


def test_silent_if_swapper_handle() -> None:
    h = SilentIfSwapper()
    h.handle(0)


def test_handlers_accept_session() -> None:
    session = MagicMock()
    h = MemberDoubleClick(session=session)
    assert h._session is session
```

### 4.5 Action files (8 files + 8 tests)

Each action class is a minimal subclass of HexRaysPopupAction (or Action for the BWN_DISASM/BWN_FUNCS variants).

Pattern for each file:

```python
"""<Brief description of the action group>."""
from __future__ import annotations
from typing import TYPE_CHECKING, Any

from ..action import Action, HexRaysPopupAction

if TYPE_CHECKING:
    from ...session import Session


class ShowGraph(Action):
    description = "Show Graph"
    hotkey = "G"
    def __init__(self, session: "Session | None" = None) -> None:
        super().__init__(session)
    def activate(self, ctx: Any) -> None:
        pass  # stub


class ShowClasses(Action):
    description = "Show Classes"
    hotkey = "Alt+F1"
    def __init__(self, session: "Session | None" = None) -> None:
        super().__init__(session)
    def activate(self, ctx: Any) -> None:
        pass


class ShowStructureBuilder(HexRaysPopupAction):
    description = "Show Structure Builder"
    hotkey = "Alt+F8"
    def __init__(self, session: "Session | None" = None) -> None:
        super().__init__(session)
    def activate(self, ctx: Any) -> None:
        pass
    def check(self, hx_view: Any) -> bool:
        return True
```

#### File list (9 files for 27 actions)

1. `form_requests.py` — ShowGraph, ShowClasses, ShowStructureBuilder (3)
2. `function_signature.py` — ConvertToUsercall, AddRemoveReturn, RemoveArgument (3)
3. `scanners.py` — ShallowScanVariable, DeepScanVariable, RecognizeShape, DeepScanReturn, DeepScanFunctions (5)
4. `struct_xref.py` — FindFieldXrefs (1)
5. `struct_creation.py` — CreateNewField, CreateVtable (2)
6. `structs_by_size.py` — GetStructureBySize (1)
7. `guess_allocation.py` — GuessAllocation (1)
8. `member_double_click.py` — MemberDoubleClickAction (1)
9. `virtual_table.py` — CreateVtableAction (1)
10. `swap_if_action.py` — SwapThenElse (1)
11. `recast_action.py` — RecastItemLeft, RecastItemRight (2)
12. `rename_action.py` — RenameOther, RenameInside, RenameOutside, RenameMemberFromFunctionName, RenameUsingAssert, PropagateName (6) — **B10 fix**: RenameMemberFromFunctionName uses Ctrl+Alt+N (not Ctrl+N)
13. `containing_structure.py` — SelectContainingStructure, ResetContainingStructure (2)

For each file, similar minimal stub pattern with description, hotkey, activate(). Tests verify the class can be instantiated.

## Verification

```bash
PYTHONPATH=src pytest tests/domain/actions/ -v
python -m mypy --strict src/hexrays_pytools/domain/actions/
python -m ruff check src/hexrays_pytools/domain/actions/ tests/domain/actions/
PYTHONPATH=src pytest  # full suite
```

## Commits

Make ONE commit per task (4.3, 4.4, 4.5 — 3 commits) for clean history:

```bash
# After 4.3
git add src/hexrays_pytools/domain/actions/hx_callback.py tests/domain/actions/test_hx_callback.py
git commit -m "feat(actions): add HxCallbackManager (Hex-Rays event dispatcher)"

# After 4.4
git add src/hexrays_pytools/domain/actions/hx_events.py tests/domain/actions/test_hx_events.py
git commit -m "feat(actions): add 4 hx event handlers (MemberDoubleClick, etc.)"

# After 4.5
git add src/hexrays_pytools/domain/actions/ tests/domain/actions/
git commit -m "feat(actions): add 27 action classes across 13 files"
```

## Report

Write 3 separate reports:
- `task-4.3-report.md`
- `task-4.4-report.md`
- `task-4.5-report.md`

Status each as DONE | DONE_WITH_CONCERNS.

After all 3 tasks, return:
- 3 commit SHAs + subjects
- Test summary (X/X pass)
- Coverage %
- 3 report paths