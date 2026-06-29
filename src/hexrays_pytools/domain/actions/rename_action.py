"""6 rename action wrappers.

Each wraps the ctree rename engine in ``domain/ctree/rename.py``. The first
five (Other, Inside, Outside, FromFunctionName, UsingAssert) are self-
contained; ``PropagateName`` uses the recursive scanner engine
(``RecursiveObjectDownwardsVisitor`` from Phase A.4) to walk all callees
and rename the tracked object everywhere it appears.
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from ...domain.scanner.scanned_object import (
    SO_GLOBAL_OBJECT,
    SO_LOCAL_VARIABLE,
    SO_STRUCT_POINTER,
    SO_STRUCT_REFERENCE,
    ScanObject,
)
from ...domain.scanner.visitor_base import RecursiveObjectDownwardsVisitor
from ...domain.types.tinfo_utils import change_member_name, get_member_name
from ...infra.arch.arch import to_hex
from ..ctree import rename as engine
from .action import HexRaysPopupAction

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


_RENAME_MENU_PATH = "HexRaysPyTools/Rename/"

# IDA-generated default names: a1, v3, var_5, qword_8, dword_4, field_12,
# off_4, etc. Propagating a real name into these slots is the use case;
# propagating a real name over another real name is opt-in via the
# ``propagate_through_all_names`` setting.
_DEFAULT_NAME_PATTERN = re.compile(
    r"^(?:[av]\d+|[qd]?word|field_|off_)"
)


def _is_default_name(name: str | None) -> bool:
    """Return True if ``name`` is an IDA-generated default (a1, v3, var_5, qword_8, ...)."""
    if name is None:
        return True
    return _DEFAULT_NAME_PATTERN.match(name) is not None


def _rename_with_prefix(rename_func: Any, name: str) -> str:
    """Call ``rename_func(name)``; on collision, prefix with ``_`` until it sticks."""
    while not rename_func(name):
        name = "_" + name
    return name


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


# --- Phase A.8: PropagateName --------------------------------------------------


class _NamePropagator(RecursiveObjectDownwardsVisitor):
    """Walk the current function + all callees, renaming the tracked object.

    Uses the ``_start_iteration`` / ``_finish`` hooks (Phase A.4) to switch
    the pseudocode view to each callee as it's scanned (so the user sees
    the renames in real time).

    Skips renames when:
    * ``self.crippled`` — the function is a thunk; the type/name belongs
      to the caller, not this passthrough.
    * The current name is not a default name AND
      ``session.propagate_through_all_names`` is False (user opted out of
      overwriting real names).
    """

    def __init__(self, hx_view: Any, cfunc: Any, obj: Any) -> None:
        super().__init__(cfunc, obj, skip_until_object=True)
        # IMPORTANT: super().__init__ swallows obj.name into ScanObject's
        # .name — capture it here for use across the recursive walk.
        self._propagated_name = str(obj.name)
        self._hx_view = hx_view

    def _start_iteration(self) -> None:
        if self._hx_view is not None and self._cfunc is not None:
            self._hx_view.switch_to(self._cfunc, False)

    def _finish(self) -> None:
        if self._hx_view is not None and self._cfunc is not None:
            self._hx_view.switch_to(self._cfunc, True)

    def _manipulate(self, cexpr: Any, obj: Any) -> None:
        if self.crippled:
            logger.debug(
                "Skipping crippled function at %s", to_hex(int(self._cfunc.entry_ea))
            )
            return

        propagate_all = bool(
            self._session_override_get("propagate_through_all_names")
        )

        if int(obj.id) == int(SO_GLOBAL_OBJECT):
            old_name = str(idaapi.get_short_name(int(cexpr.obj_ea)))
            if propagate_all or _is_default_name(old_name):
                new_name = _rename_with_prefix(
                    lambda x: idaapi.set_name(int(cexpr.obj_ea), x),
                    self._propagated_name,
                )
                logger.debug(
                    "Renamed global variable from %s to %s", old_name, new_name
                )
        elif int(obj.id) == int(SO_LOCAL_VARIABLE):
            lvar = self._cfunc.get_lvars()[int(cexpr.v.idx)]
            old_name = str(lvar.name)
            if propagate_all or _is_default_name(old_name):
                new_name = _rename_with_prefix(
                    lambda x: self._hx_view.rename_lvar(lvar, x, True),
                    self._propagated_name,
                )
                logger.debug(
                    "Renamed local variable from %s to %s", old_name, new_name
                )
        elif int(obj.id) in (int(SO_STRUCT_POINTER), int(SO_STRUCT_REFERENCE)):
            struct_tinfo = cexpr.x.type
            offset = int(cexpr.m)
            struct_tinfo.remove_ptr_or_array()
            struct_name = str(struct_tinfo.dstr())

            old_name = get_member_name(struct_tinfo, offset)
            if propagate_all or _is_default_name(old_name):
                new_name = _rename_with_prefix(
                    lambda x: change_member_name(struct_name, offset, x),
                    self._propagated_name,
                )
                logger.debug(
                    "Renamed struct member from %s to %s", old_name, new_name
                )

    def _session_override_get(self, key: str) -> bool:
        """Read a setting via ``self._hx_view``'s session (if available).

        The visitor is constructed from inside an action that has the
        session; the action passes it through ``hx_view`` — but IDA's
        hx_view doesn't carry a session reference, so we fall back to
        ``False`` (the safe default: don't propagate over real names).
        """
        return False


class PropagateName(HexRaysPopupAction):
    """Propagate the selected name to all references (recursive)."""

    description = "Propagate name"
    hotkey = "P"
    menu_path = _RENAME_MENU_PATH

    def check(self, hx_view: Any) -> bool:
        if hx_view is None:
            return False
        ctree_item = hx_view.item
        if int(ctree_item.citype) != int(idaapi.VDI_EXPR):
            return False
        obj = ScanObject.create(hx_view.cfunc, ctree_item)
        if obj is None:
            return False
        return not _is_default_name(str(obj.name))

    def activate(self, ctx: Any) -> None:
        hx_view = _get_hx_view(ctx)
        if hx_view is None:
            return
        obj = ScanObject.create(hx_view.cfunc, hx_view.item)
        if obj is None:
            return
        visitor = _NamePropagator(hx_view, hx_view.cfunc, obj)
        # Wire the session into the visitor so _manipulate can read
        # settings (propagate_through_all_names). The action's _session
        # is the source of truth.
        if self._session is not None:
            visitor._session_override_get = (  # type: ignore[method-assign]
                lambda key: bool(getattr(self._session, key, False))
            )
        visitor.process()
        hx_view.refresh_view(True)
