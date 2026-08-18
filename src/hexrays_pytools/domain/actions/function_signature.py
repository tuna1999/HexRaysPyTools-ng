"""Function signature modifier actions (ConvertToUsercall, AddRemoveReturn, RemoveArgument).

Ported from the original `callbacks/function_signature_modifiers.py` (91 LOC).
These operate on the current function's ``func_type_data_t`` and re-apply the
modified type via ``apply_tinfo``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from .action import HexRaysPopupAction

if TYPE_CHECKING:
    pass


def _get_func_tinfo(vu: Any) -> Any:
    """Fill and return a tinfo_t with the current function's type, or None."""
    function_tinfo = idaapi.tinfo_t()
    if not vu.cfunc.get_func_type(function_tinfo):
        return None
    return function_tinfo


class ConvertToUsercall(HexRaysPopupAction):
    """Convert the current function signature to __usercall."""

    description = "Convert to __usercall"
    menu_path = "HexRaysPyTools/Function/"

    def check(self, hx_view: Any) -> bool:
        return hx_view is not None and hx_view.item.citype == idaapi.VDI_FUNC

    def activate(self, ctx: Any) -> None:
        vu = idaapi.get_widget_vdui(ctx.widget)
        if vu is None:
            return
        function_tinfo = _get_func_tinfo(vu)
        if function_tinfo is None:
            return
        function_details = idaapi.func_type_data_t()
        function_tinfo.get_func_details(function_details)
        convention = idaapi.CM_CC_MASK & function_details.cc
        if convention == idaapi.CM_CC_CDECL:
            function_details.cc = idaapi.CM_CC_SPECIAL
        elif convention in (
            idaapi.CM_CC_STDCALL,
            idaapi.CM_CC_FASTCALL,
            idaapi.CM_CC_PASCAL,
            idaapi.CM_CC_THISCALL,
        ):
            function_details.cc = idaapi.CM_CC_SPECIALP
        elif convention == idaapi.CM_CC_ELLIPSIS:
            function_details.cc = idaapi.CM_CC_SPECIALE
        else:
            return
        function_tinfo.create_func(function_details)
        idaapi.apply_tinfo(int(vu.cfunc.entry_ea), function_tinfo, idaapi.TINFO_DEFINITE)
        vu.refresh_view(True)


class AddRemoveReturn(HexRaysPopupAction):
    """Toggle a return value on the current function (void ↔ void *)."""

    description = "Add/Remove Return"
    menu_path = "HexRaysPyTools/Function/"

    def check(self, hx_view: Any) -> bool:
        return hx_view is not None and hx_view.item.citype == idaapi.VDI_FUNC

    def activate(self, ctx: Any) -> None:
        vu = idaapi.get_widget_vdui(ctx.widget)
        if vu is None:
            return
        function_tinfo = _get_func_tinfo(vu)
        if function_tinfo is None:
            return
        function_details = idaapi.func_type_data_t()
        function_tinfo.get_func_details(function_details)
        void_tinfo = idaapi.tinfo_t(idaapi.BT_VOID)
        if function_details.rettype.equals_to(void_tinfo):
            # void → void *
            pvoid = idaapi.tinfo_t()
            pvoid.create_ptr(void_tinfo)
            function_details.rettype = pvoid
        else:
            # anything → void
            function_details.rettype = void_tinfo
        function_tinfo.create_func(function_details)
        idaapi.apply_tinfo(int(vu.cfunc.entry_ea), function_tinfo, idaapi.TINFO_DEFINITE)
        vu.refresh_view(True)


class RemoveArgument(HexRaysPopupAction):
    """Remove the selected argument from the function signature."""

    description = "Remove Argument"
    menu_path = "HexRaysPyTools/Function/"

    def check(self, hx_view: Any) -> bool:
        if hx_view is None or hx_view.item.citype != idaapi.VDI_LVAR:
            return False
        local_variable = hx_view.item.get_lvar()
        return bool(local_variable.is_arg_var())

    def activate(self, ctx: Any) -> None:
        vu = idaapi.get_widget_vdui(ctx.widget)
        if vu is None:
            return
        function_tinfo = _get_func_tinfo(vu)
        if function_tinfo is None:
            return
        function_details = idaapi.func_type_data_t()
        function_tinfo.get_func_details(function_details)
        del_arg = vu.item.get_lvar()
        matches = [x for x in function_details if x.name == del_arg.name]
        if not matches:
            return
        function_details.erase(matches[0])
        function_tinfo.create_func(function_details)
        idaapi.apply_tinfo(int(vu.cfunc.entry_ea), function_tinfo, idaapi.TINFO_DEFINITE)
        vu.refresh_view(True)
