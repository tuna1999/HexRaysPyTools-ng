"""Thin wrappers around idaapi tinfo_t methods.

Extracted from the original `core/helper.py` so other modules can mock
the IDA API in tests. Pure functions where possible; IDA-coupled where
unavoidable.
"""
from __future__ import annotations

import logging

import idaapi  # type: ignore[import-not-found]
import idc  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


def get_ordinal(tinfo: idaapi.tinfo_t) -> int:
    """Get the local-type ordinal of `tinfo`, or 0 if not a local type."""
    if tinfo.is_udt() or tinfo.is_enum():
        return int(tinfo.get_ordinal())
    if tinfo.is_typeref():
        return int(tinfo.get_ordinal())
    return 0


def get_nice_pointed_object(tinfo: idaapi.tinfo_t) -> idaapi.tinfo_t:
    """Strip the `P` prefix from pointed object name if a matching type exists."""
    inner = tinfo.get_pointed_object()
    if not inner:
        return inner
    name = idaapi.get_short_name(inner.dstr())
    if name.startswith("P"):
        candidate = name[1:]
        named = idaapi.tinfo_t()
        if named.get_named_type(idaapi.get_idati(), candidate):
            return named
    return inner


def get_member_name(tinfo: idaapi.tinfo_t, offset: int) -> str:
    """Get the member name at the byte `offset` of struct/union `tinfo`.

    Mirrors the original `helper.get_member_name`.
    """
    udt_member = idaapi.udt_member_t()
    udt_member.offset = offset * 8  # bytes → bits
    tinfo.find_udt_member(udt_member, idaapi.STRMEM_OFFSET)
    return str(udt_member.name)


def change_member_name(struct_name: str, offset: int, name: str) -> bool:
    """Rename a struct member by struct name + byte offset.

    Mirrors the original `helper.change_member_name`.
    """
    return bool(idc.set_member_name(idc.get_struc_id(struct_name), offset, name))


def is_legal_type(tinfo: idaapi.tinfo_t) -> bool:
    """Return True if ``tinfo`` is a type the scanner engine can apply.

    Mirrors the original ``core/helper.py:is_legal_type``. A tinfo is legal
    unless it's an unknown type. Forward declarations of pointer targets are
    legal as long as the target size is known (``!BADSIZE``) — the scanner
    uses these to apply char/wide-char pointer types.

    Note: the original ``clr_const()`` mutates the input in-place. The new
    plugin ports the behaviour but logs a debug message instead of mutating
    — mutating the caller's tinfo is a hidden side effect the rule book
    (common/coding-style.md, "Immutability CRITICAL") forbids.
    """
    if tinfo is None:
        return False
    if tinfo.is_ptr() and tinfo.get_pointed_object().is_forward_decl():
        is_bad_size = tinfo.get_pointed_object().get_size() == idaapi.BADSIZE
        logger.debug(
            "Type %s is forward declaration: %s", str(tinfo.dstr()), is_bad_size
        )
        return not is_bad_size
    if tinfo.is_unknown():
        logger.debug("Type %s is unknown", str(tinfo.dstr()))
        return False
    return True
