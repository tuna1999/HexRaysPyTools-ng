"""6 rename action wrappers.

Each wraps the ctree rename engine in ``domain/ctree/rename.py``. The first
five (Other, Inside, Outside, FromFunctionName, UsingAssert) are self-
contained; ``PropagateName`` needs the recursive scanner engine and stays a
no-op until that lands.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from ..ctree import rename as engine
from .action import HexRaysPopupAction

if TYPE_CHECKING:
    pass


_RENAME_MENU_PATH = "HexRaysPyTools/Rename/"


def _get_hx_view(ctx: Any) -> Any:
    return idaapi.get_widget_vdui(ctx.widget)


class RenameOther(HexRaysPopupAction):
    """Take the other variable's name in an assignment (a = b → a = b's name)."""

    description = "Take other name"
    hotkey = "Ctrl+N"
    menu_path = _RENAME_MENU_PATH

    def check(self, hx_view: Any) -> bool:
        if hx_view is None:
            return False
        return engine.extract_rename_other_info(hx_view.cfunc, hx_view.item) is not None

    def activate(self, ctx: Any) -> None:
        hx_view = _get_hx_view(ctx)
        if hx_view is None:
            return
        info = engine.extract_rename_other_info(hx_view.cfunc, hx_view.item)
        if info is not None:
            engine.rename_other(hx_view, info)


class RenameInside(HexRaysPopupAction):
    """Push the variable's name into the called function's parameter."""

    description = "Rename inside argument"
    hotkey = "Shift+Alt+N"
    menu_path = _RENAME_MENU_PATH

    def check(self, hx_view: Any) -> bool:
        if hx_view is None:
            return False
        return engine.extract_rename_inside_info(hx_view.cfunc, hx_view.item) is not None

    def activate(self, ctx: Any) -> None:
        hx_view = _get_hx_view(ctx)
        if hx_view is None:
            return
        info = engine.extract_rename_inside_info(hx_view.cfunc, hx_view.item)
        if info is not None:
            engine.rename_inside(hx_view, info)


class RenameOutside(HexRaysPopupAction):
    """Take the called function's parameter name for a local variable."""

    description = "Take argument name"
    hotkey = "Ctrl+Shift+N"
    menu_path = _RENAME_MENU_PATH

    def check(self, hx_view: Any) -> bool:
        if hx_view is None:
            return False
        return engine.extract_rename_outside_info(hx_view.cfunc, hx_view.item) is not None

    def activate(self, ctx: Any) -> None:
        hx_view = _get_hx_view(ctx)
        if hx_view is None:
            return
        info = engine.extract_rename_outside_info(hx_view.cfunc, hx_view.item)
        if info is not None:
            engine.rename_outside(hx_view, info)


class RenameMemberFromFunctionName(HexRaysPopupAction):
    """Infer a struct member name from the enclosing getter/setter function."""

    description = "Take name from function"
    hotkey = "Ctrl+Alt+N"
    menu_path = _RENAME_MENU_PATH

    def check(self, hx_view: Any) -> bool:
        if hx_view is None:
            return False
        return engine.extract_member_from_func_info(hx_view.cfunc, hx_view.item) is not None

    def activate(self, ctx: Any) -> None:
        hx_view = _get_hx_view(ctx)
        if hx_view is None:
            return
        info = engine.extract_member_from_func_info(hx_view.cfunc, hx_view.item)
        if info is not None:
            engine.rename_member_from_function_name(hx_view, info)


class RenameUsingAssert(HexRaysPopupAction):
    """Rename all callers of an assert-like function by its string argument."""

    description = "Rename as assert argument"
    hotkey = None
    menu_path = _RENAME_MENU_PATH

    def check(self, hx_view: Any) -> bool:
        if hx_view is None:
            return False
        return engine.extract_assert_info(hx_view.cfunc, hx_view.item)

    def activate(self, ctx: Any) -> None:
        hx_view = _get_hx_view(ctx)
        if hx_view is None:
            return
        engine.rename_using_assert(hx_view, hx_view.cfunc, hx_view.item)


class PropagateName(HexRaysPopupAction):
    """Propagate the selected name to all references (needs scanner engine).

    Stub until the ``RecursiveObjectDownwardsVisitor`` engine lands; never
    enabled in the menu for now.
    """

    description = "Propagate name"
    hotkey = "P"
    menu_path = _RENAME_MENU_PATH

    def check(self, hx_view: Any) -> bool:
        return False  # disabled until scanner engine ports

    def activate(self, ctx: Any) -> None:
        pass
