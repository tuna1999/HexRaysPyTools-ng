"""Struct field xref action (FindFieldXrefs).

Ported from the original `callbacks/struct_xref_representation.py` (85 LOC).
Works in two widgets: pseudocode (cursor on a struct field access) and the
Local Types view (cursor on a struct member). Shows a chooser of all stored
field cross-references and jumps to the selected one.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]
import idc  # type: ignore[import-not-found]

from ...ui.chooser import MyChoose
from ..types.tinfo_utils import get_member_name, get_ordinal
from ..xrefs.xref_storage import XrefStorage
from .action import HexRaysXrefAction

if TYPE_CHECKING:
    from ..session import Session


class FindFieldXrefs(HexRaysXrefAction):
    """Show cross-references to the selected struct field."""

    description = "Field Xrefs"
    hotkey = "Ctrl+X"
    menu_path = "HexRaysPyTools/Structure/"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def check(self, hx_view: Any) -> bool:
        if hx_view is None:
            return False
        item = hx_view.item
        return bool(
            item.citype == idaapi.VDI_EXPR
            and item.it.to_specific_type.op in (idaapi.cot_memptr, idaapi.cot_memref)
        )

    def activate(self, ctx: Any) -> None:
        ordinal = 0
        offset = 0
        struct_name = ""
        field_name = ""

        if ctx.widget_type == idaapi.BWN_PSEUDOCODE:
            hx_view = idaapi.get_widget_vdui(ctx.widget)
            if hx_view is None:
                return
            item = hx_view.item
            if not self.check(hx_view):
                return
            offset = int(item.e.m)
            struct_type = item.e.x.type.remove_ptr_or_array()
            ordinal = get_ordinal(struct_type)
            struct_name = str(struct_type.dstr())
            field_name = get_member_name(struct_type, offset)
        elif ctx.widget_type == idaapi.BWN_TILIST:
            ordinal = int(ctx.cur_struc.ordinal)
            offset = int(ctx.cur_strmem.soff)
            struct_name = str(idc.get_struc_name(int(ctx.cur_struc.id)))
            field_name = str(idc.get_member_name(int(ctx.cur_strmem.id)))
        else:
            return

        xrefs = XrefStorage().get_structure_info(ordinal=ordinal, func_offset=offset)
        data: list[list[str]] = []
        for xref_info in xrefs:
            data.append(
                [
                    str(idaapi.get_short_name(int(xref_info[0])))
                    + "+"
                    + hex(int(xref_info[1])),
                    str(xref_info[2]),
                    str(xref_info[3]),
                ]
            )

        chooser = MyChoose(
            data,
            f"Cross-references to {struct_name}::{field_name}",
            [
                ["Function", 20 | idaapi.Choose.CHCOL_PLAIN],
                ["Type", 2 | idaapi.Choose.CHCOL_PLAIN],
                ["Line", 40 | idaapi.Choose.CHCOL_PLAIN],
            ],
        )
        idx = chooser.Show(True)
        if idx == -1:
            return

        xref = xrefs[idx]
        # xref_info is (func_offset, field_ea, access_type, line) — open at func.
        idaapi.open_pseudocode(int(xref[0]), False)
