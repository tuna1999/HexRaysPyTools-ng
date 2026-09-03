"""Find structures matching a size (GetStructureBySize).

Ported from the original `callbacks/structs_by_size.py` (77 LOC). Right-click
on a number literal → list library structs of that size → render the literal
as ``sizeof(StructName)`` and import the type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from ..chooser import MyChoose
from ..til.type_library import choose_til, import_type
from .action import HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


def _choose_structure_by_size(size: int) -> int | None:
    """Pick a library struct whose size == `size`. Returns its ordinal or None."""
    result = choose_til()
    if not result:
        return None
    selected_library, max_ordinal, is_local_type = result
    matched_types: list[list[str]] = []
    tinfo = idaapi.tinfo_t()
    for ordinal in range(1, max_ordinal):
        tinfo.create_typedef(selected_library, ordinal)
        if tinfo.get_size() == size:
            name = str(tinfo.dstr())
            description = str(idaapi.print_tinfo(None, 0, 0, idaapi.PRTYPE_DEF, tinfo, None, None))
            matched_types.append([str(ordinal), name, description])

    chooser = MyChoose(
        matched_types,
        "Select Type",
        [
            ["Ordinal", 5 | idaapi.Choose.CHCOL_HEX],
            ["Type Name", 25],
            ["Declaration", 50],
        ],
        165,
    )
    selected_type = chooser.Show(True)
    if selected_type == -1:
        return None
    if is_local_type:
        return int(matched_types[selected_type][0])
    return import_type(selected_library, matched_types[selected_type][1])


class GetStructureBySize(HexRaysPopupAction):
    """List existing structures whose size matches the selected number literal."""

    description = "Structures with this size"
    menu_path = "HexRaysPyTools-ng/"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def check(self, hx_view: Any) -> bool:
        if hx_view is None:
            return False
        item = hx_view.item
        return bool(item.citype == idaapi.VDI_EXPR and item.e.op == idaapi.cot_num)

    def activate(self, ctx: Any) -> None:
        hx_view = idaapi.get_widget_vdui(ctx.widget)
        if hx_view is None or not self.check(hx_view):
            return
        ea = int(ctx.cur_ea)
        c_number = hx_view.item.e
        number_value = c_number.numval()
        ordinal = _choose_structure_by_size(int(number_value))
        if not ordinal:
            return

        number_format_old = c_number.n.nf
        number_format_new = idaapi.number_format_t()
        number_format_new.flags = idaapi.FF_1STRO | idaapi.FF_0STRO
        operand_number = number_format_old.opnum
        number_format_new.opnum = operand_number
        number_format_new.props = number_format_old.props
        number_format_new.type_name = idaapi.get_numbered_type_name(
            idaapi.get_idati(), int(ordinal)
        )

        c_function = hx_view.cfunc
        number_formats = c_function.numforms
        operand_locator = idaapi.operand_locator_t(ea, ord(operand_number) if operand_number else 0)
        if operand_locator in number_formats:
            del number_formats[operand_locator]
        number_formats[operand_locator] = number_format_new
        c_function.save_user_numforms()
        hx_view.refresh_view(True)
