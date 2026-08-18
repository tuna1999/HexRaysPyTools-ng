"""Struct field xref action (FindFieldXrefs).

Ported from the original `callbacks/struct_xref_representation.py` (85 LOC).
Works in two widgets: pseudocode (cursor on a struct field access) and the
Local Types view (cursor on a struct member). Shows a chooser of all stored
field cross-references and jumps to the selected one.

Reads via ``session.xrefs`` (Session-owned ``XrefStorage``); never instantiates
a fresh ``XrefStorage`` — that would bypass the in-memory cache and miss
entries collected during the current session.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from ..chooser import MyChoose
from ..types.tinfo_utils import get_member_name, get_ordinal
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
        field_offset = 0
        struct_name = ""
        field_name = ""

        if ctx.widget_type == idaapi.BWN_PSEUDOCODE:
            hx_view = idaapi.get_widget_vdui(ctx.widget)
            if hx_view is None:
                return
            item = hx_view.item
            if not self.check(hx_view):
                return
            field_offset = int(item.e.m)
            struct_type = idaapi.tinfo_t(item.e.x.type)
            struct_type.remove_ptr_or_array()
            ordinal = get_ordinal(struct_type)
            struct_name = str(struct_type.dstr())
            field_name = get_member_name(struct_type, field_offset)
        elif self._is_local_types_widget(ctx.widget_type):
            type_ref = ctx.type_ref
            if type_ref is None or not type_ref.on_member() or not type_ref.is_udt():
                return
            ordinal = int(type_ref.ordinal)
            # IDA 9 exposes the current Local Types UDT member as ``udm``;
            # its offset uses bits, while XrefStorage keys use byte offsets.
            field_offset = int(type_ref.udm.offset) // 8
            struct_name = str(type_ref.tif.dstr())
            field_name = str(type_ref.udm.name)
        else:
            return

        # Query the Session-owned storage (NOT a fresh XrefStorage() — that
        # would bypass the in-memory cache and read un-persisted data). The
        # query key is (ordinal, field_offset); storage iterates all functions.
        storage = self._session.xrefs if self._session is not None else None
        if storage is None:
            return
        xrefs = storage.get_structure_info(ordinal=ordinal, field_offset=field_offset)
        # Each entry is (func_ea, occurrence_offset, line, usage_type).
        data: list[list[str]] = []
        for xref_info in xrefs:
            data.append(
                [
                    str(idaapi.get_short_name(int(xref_info[0]))) + "+" + hex(int(xref_info[1])),
                    str(xref_info[3]),
                    str(xref_info[2]),
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
        # Jump to the function at func_ea + occurrence_offset.
        idaapi.open_pseudocode(int(xref[0]) + int(xref[1]), False)
