"""UDT (struct/union) builder from member list.

Pure-ish: takes a list of (name, offset, size, tinfo) tuples and returns
a udt_type_data_t ready to be applied to a Local Type.

Extracted from the original `core/temporary_structure.py:pack()` method.
"""
from __future__ import annotations

import idaapi  # type: ignore[import-not-found]


def create_padding_udt_member(offset: int, size: int) -> idaapi.udt_member_t:
    """Create a gap_<offset> padding udt_member."""
    member = idaapi.udt_member_t()
    member.name = f"gap_{offset:X}"
    member.offset = offset
    # Padding type: byte array of `size` bytes
    pad_type = idaapi.tinfo_t()
    pad_type.create_array(idaapi.tinfo_t(idaapi.BT_BYTE), size)
    member.type = pad_type
    member.size = size
    return member
