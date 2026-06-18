"""Thin wrappers around idaapi tinfo_t methods.

Extracted from the original `core/helper.py` so other modules can mock
the IDA API in tests. Pure functions where possible; IDA-coupled where
unavoidable.
"""
from __future__ import annotations

import idaapi  # type: ignore[import-not-found]


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
