"""Struct creation actions (CreateNewField, CreateVtable).

Ported from the original `callbacks/new_field_creation.py` (137 LOC) and
`callbacks/virtual_table_creation.py` (34 LOC).
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]
import idc  # type: ignore[import-not-found]

from ..recon.discovered_vtable import DiscoveredVTable
from ..types.tinfo_utils import get_member_name
from ..types.udt_builder import create_padding_udt_member
from .action import Action, HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session

logger = logging.getLogger(__name__)


def _is_gap_field(cexpr: Any) -> bool:
    """Return True if `cexpr` accesses a gap_<X> padding member."""
    if cexpr.op not in (idaapi.cot_memptr, idaapi.cot_memref):
        return False
    struct_type = cexpr.x.type
    struct_type.remove_ptr_or_array()
    return get_member_name(struct_type, int(cexpr.m))[0:3] == "gap"


class CreateNewField(HexRaysPopupAction):
    """Split a gap_ padding field into a real typed field at the cursor."""

    description = "Create New Field"
    hotkey = "Ctrl+F"
    menu_path = "HexRaysPyTools-ng/"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def check(self, hx_view: Any) -> bool:
        if hx_view is None:
            return False
        if hx_view.item.citype != idaapi.VDI_EXPR:
            return False
        return _is_gap_field(hx_view.item.it.to_specific_type)

    def activate(self, ctx: Any) -> None:
        hx_view = idaapi.get_widget_vdui(ctx.widget)
        if hx_view is None or not self.check(hx_view):
            return

        item = hx_view.item.it.to_specific_type
        parent = hx_view.cfunc.body.find_parent_of(item).to_specific_type
        if parent.op != idaapi.cot_idx or parent.y.op != idaapi.cot_num:
            idx = 0
        else:
            idx = parent.y.numval()

        struct_tinfo = item.x.type
        struct_tinfo.remove_ptr_or_array()

        offset = int(item.m)
        ordinal = int(struct_tinfo.get_ordinal())
        struct_name = str(struct_tinfo.dstr())

        if (offset + idx) % 2:
            default_field_type = "_BYTE"
        elif (offset + idx) % 4:
            default_field_type = "_WORD"
        elif (offset + idx) % 8:
            default_field_type = "_DWORD"
        else:
            default_field_type = "_QWORD" if idaapi.inf_is_64bit() else "_DWORD"

        declaration = idaapi.ask_text(
            0x10000,
            f"{default_field_type} field_{offset + idx:X}",
            "Enter new structure member:",
        )
        if declaration is None:
            return

        parsed = self._parse_declaration(str(declaration))
        if parsed is None:
            logger.warning("Bad member declaration")
            return
        field_tinfo, field_name = parsed
        field_size = int(field_tinfo.get_size())
        udt_data = idaapi.udt_type_data_t()
        udt_member = idaapi.udt_member_t()

        struct_tinfo.get_udt_details(udt_data)
        udt_member.offset = offset * 8
        struct_tinfo.find_udt_member(udt_member, idaapi.STRMEM_OFFSET)
        gap_size = int(udt_member.size) // 8
        gap_leftover = gap_size - idx - field_size
        if gap_leftover < 0:
            logger.error("Too big size for the field. Max %d bytes", gap_size - idx)
            return

        it = udt_data.find(udt_member)
        it = udt_data.erase(it)

        if gap_leftover > 0:
            udt_data.insert(
                it,
                create_padding_udt_member(offset + idx + field_size, gap_leftover),
            )

        new_member = idaapi.udt_member_t()
        new_member.offset = (offset + idx) * 8
        new_member.name = field_name
        new_member.type = field_tinfo
        new_member.size = field_size * 8
        it = udt_data.insert(it, new_member)

        if idx > 0:
            udt_data.insert(it, create_padding_udt_member(offset, idx))

        struct_tinfo.create_udt(udt_data, idaapi.BTF_STRUCT)
        struct_tinfo.set_numbered_type(
            idaapi.get_idati(), ordinal, idaapi.NTF_REPLACE, struct_name
        )
        hx_view.refresh_view(True)

    @staticmethod
    def _parse_declaration(declaration: str) -> tuple[Any, str] | None:
        """Parse 'TYPE_NAME NAME' or 'TYPE_NAME NAME[SIZE]' → (tinfo, name)."""
        m = re.search(r"^(\w+[ *]+)(\w+)(\[(\d+)\])?$", declaration)
        if m is None:
            logger.error(
                "Member declaration should be like `TYPE_NAME NAME[SIZE]` (array is optional)"
            )
            return None
        type_name, field_name, _, arr_size = m.groups()
        if field_name[0].isdigit():
            logger.error("Bad field name")
            return None
        result = idc.parse_decl(type_name, 0)
        if result is None:
            logger.error("Failed to parse member type")
            return None
        _, tp, fld = result
        tinfo = idaapi.tinfo_t()
        tinfo.deserialize(idaapi.get_idati(), tp, fld, None)
        if arr_size and not tinfo.create_array(tinfo, int(arr_size)):
            return None
        return tinfo, field_name


class CreateVtable(Action):
    """Create a virtual table from the struct pointer at the cursor (disasm)."""

    description = "Create Virtual Table"
    hotkey = "V"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    @staticmethod
    def check(ea: int) -> bool:
        return ea != idaapi.BADADDR and bool(DiscoveredVTable.check_address(int(ea)))

    def activate(self, ctx: Any) -> None:
        ea = int(ctx.cur_ea)
        if not self.check(ea):
            return
        vtable = DiscoveredVTable(
            offset=0,
            tinfo=None,
            name="__vftable",
            origin=0,
            address=ea,
        )
        # Preserve upstream behavior: show the generated declaration before
        # committing a new Local Type.
        vtable.import_to_structures(ask=True)
        hx_view = idaapi.get_widget_vdui(ctx.widget) if hasattr(ctx, "widget") else None
        if hx_view is not None:
            hx_view.refresh_view(True)

    def update(self, ctx: Any) -> int:
        if ctx.widget_type == idaapi.BWN_DISASM:
            if self.check(int(ctx.cur_ea)):
                idaapi.attach_action_to_popup(ctx.widget, None, self.name)
                return int(idaapi.AST_ENABLE)
            idaapi.detach_action_from_popup(ctx.widget, self.name)
            return int(idaapi.AST_DISABLE)
        return int(idaapi.AST_DISABLE_FOR_WIDGET)
