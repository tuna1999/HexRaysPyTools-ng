"""IDA session-scoped tinfo singletons + type library constants.

Ported from the original ``core/const.py``. The original plugin held these
as module-level globals (re-initialized via ``const.init()`` at
session open). Here they live on a :class:`Consts` dataclass owned by
:class:`Session`, so the lifetime is explicit and the dataclass itself is
pure data (testable in isolation).

The tinfo singletons reference the active IDA type library, so they MUST be
re-built every time the user opens a new IDB. The plugin's
:meth:`Session.open` calls :func:`init_consts` and stores the result on
``session.consts``.

Field naming convention: snake_case to match Python idioms (the original used
``UPPER_SNAKE_CASE`` because they were module globals). The dataclass attribute
name is the canonical reference; callers should never reach into the
``Consts`` internals — pass the dataclass around or read individual fields.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import idaapi  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


@dataclass
class Consts:
    """Per-session singleton container for type-library globals.

    All tinfo fields are populated by :func:`init_consts` for the currently
    open IDB. ``legal_types`` is a convenience list of the "safe" pointer
    types the scanner engine falls back to when a member's tinfo cannot be
    inferred.
    """

    ea64: bool
    """True if the current IDB is 64-bit (pointer size 8 bytes)."""
    ea_size: int
    """Pointer size in bytes (4 or 8) — mirrors ``idaapi.inf_is_64bit()``."""

    void_tinfo: idaapi.tinfo_t
    """``void`` tinfo."""
    pvoid_tinfo: idaapi.tinfo_t
    """``void *`` tinfo."""
    const_void_tinfo: idaapi.tinfo_t
    """``const void`` tinfo."""
    const_pvoid_tinfo: idaapi.tinfo_t
    """``const void *`` tinfo."""

    char_tinfo: idaapi.tinfo_t
    """``char`` tinfo."""
    pchar_tinfo: idaapi.tinfo_t
    """``char *`` tinfo."""
    const_pchar_tinfo: idaapi.tinfo_t
    """``const char *`` tinfo."""

    byte_tinfo: idaapi.tinfo_t
    """``_BYTE`` (1-byte) tinfo."""
    pbyte_tinfo: idaapi.tinfo_t
    """Pointer-to-byte tinfo (1-byte pointed object)."""

    word_tinfo: idaapi.tinfo_t
    """``_WORD`` (2-byte) tinfo."""
    pword_tinfo: idaapi.tinfo_t
    """Pointer-to-word tinfo."""

    x_word_tinfo: idaapi.tinfo_t
    """Word-sized unknown (``_DWORD`` on x32, ``_QWORD`` on x64)."""
    px_word_tinfo: idaapi.tinfo_t
    """Pointer to the x-word-sized unknown above."""

    dummy_func: idaapi.tinfo_t
    """``void *(void)`` — placeholder function tinfo used when we know
    something is a function but cannot resolve its signature."""

    legal_types: list[idaapi.tinfo_t]
    """Convenience list of the safe fallback tinfos. Order matters — the
    scanner engine uses it for ``is_legal_type()`` membership checks."""


def init_consts() -> Consts:
    """Build a fresh :class:`Consts` for the currently open IDB.

    Mirrors the original ``core/const.init()``. Must be called from inside
    IDA (real or mocked) because it touches ``idaapi.tinfo_t`` constructors.
    Re-call this whenever the user opens a different database — the
    tinfos are tied to the active type library.
    """
    ea64 = bool(idaapi.inf_is_64bit())
    ea_size = 8 if ea64 else 4

    # --- void family --------------------------------------------------------
    void_tinfo = idaapi.tinfo_t(idaapi.BT_VOID)
    pvoid_tinfo = idaapi.tinfo_t()
    pvoid_tinfo.create_ptr(void_tinfo)
    const_void_tinfo = idaapi.tinfo_t(idaapi.BT_VOID | idaapi.BTM_CONST)
    const_pvoid_tinfo = idaapi.tinfo_t()
    const_pvoid_tinfo.create_ptr(idaapi.tinfo_t(idaapi.BT_VOID | idaapi.BTM_CONST))

    # --- char family --------------------------------------------------------
    const_pchar_tinfo = idaapi.tinfo_t()
    const_pchar_tinfo.create_ptr(idaapi.tinfo_t(idaapi.BTF_CHAR | idaapi.BTM_CONST))
    char_tinfo = idaapi.tinfo_t(idaapi.BTF_CHAR)
    pchar_tinfo = idaapi.tinfo_t()
    pchar_tinfo.create_ptr(idaapi.tinfo_t(idaapi.BTF_CHAR))

    # --- byte / word families ----------------------------------------------
    byte_tinfo = idaapi.tinfo_t(idaapi.BTF_BYTE)
    pbyte_tinfo = idaapi.dummy_ptrtype(1, False)
    x_word_tinfo = idaapi.get_unk_type(ea_size)
    px_word_tinfo = idaapi.dummy_ptrtype(ea_size, False)

    word_tinfo = idaapi.tinfo_t(idaapi.BT_UNK_WORD)
    pword_tinfo = idaapi.tinfo_t()
    pword_tinfo.create_ptr(idaapi.tinfo_t(idaapi.BT_UNK_WORD))

    # --- dummy function -----------------------------------------------------
    func_data = idaapi.func_type_data_t()
    func_data.rettype = pvoid_tinfo
    func_data.cc = idaapi.CM_CC_UNKNOWN
    dummy_func = idaapi.tinfo_t()
    dummy_func.create_func(func_data, idaapi.BT_FUNC)

    # --- legal-types list ---------------------------------------------------
    legal_types: list[idaapi.tinfo_t] = [
        pvoid_tinfo,
        px_word_tinfo,
        pword_tinfo,
        pbyte_tinfo,
        x_word_tinfo,
    ]

    logger.debug(
        "Consts initialized (ea64=%s, ea_size=%d, legal_types=%d)",
        ea64, ea_size, len(legal_types),
    )
    return Consts(
        ea64=ea64,
        ea_size=ea_size,
        void_tinfo=void_tinfo,
        pvoid_tinfo=pvoid_tinfo,
        const_void_tinfo=const_void_tinfo,
        const_pvoid_tinfo=const_pvoid_tinfo,
        char_tinfo=char_tinfo,
        pchar_tinfo=pchar_tinfo,
        const_pchar_tinfo=const_pchar_tinfo,
        byte_tinfo=byte_tinfo,
        pbyte_tinfo=pbyte_tinfo,
        word_tinfo=word_tinfo,
        pword_tinfo=pword_tinfo,
        x_word_tinfo=x_word_tinfo,
        px_word_tinfo=px_word_tinfo,
        dummy_func=dummy_func,
        legal_types=legal_types,
    )
