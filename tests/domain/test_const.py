"""Test the tinfo singleton container (domain/const.py)."""
from __future__ import annotations

import idaapi  # type: ignore[import-not-found]  # via mock_ida

from hexrays_pytools.domain.const import Consts, init_consts
from hexrays_pytools.domain.session import Session

# --- Consts dataclass shape ---------------------------------------------------


def test_consts_is_importable() -> None:
    """The Consts dataclass can be imported."""
    # The import above already proved this; the assertion is for clarity.
    assert Consts is not None


def test_consts_can_be_constructed_manually() -> None:
    """A Consts can be built with explicit fields (no IDA call needed).

    This is the value of using a dataclass: callers can construct one in
    tests without going through `init_consts()`.
    """
    c = Consts(
        ea64=True,
        ea_size=8,
        void_tinfo=idaapi.tinfo_t(idaapi.BT_VOID),
        pvoid_tinfo=idaapi.tinfo_t(),
        const_void_tinfo=idaapi.tinfo_t(),
        const_pvoid_tinfo=idaapi.tinfo_t(),
        char_tinfo=idaapi.tinfo_t(),
        pchar_tinfo=idaapi.tinfo_t(),
        const_pchar_tinfo=idaapi.tinfo_t(),
        byte_tinfo=idaapi.tinfo_t(),
        pbyte_tinfo=idaapi.tinfo_t(),
        word_tinfo=idaapi.tinfo_t(),
        pword_tinfo=idaapi.tinfo_t(),
        x_word_tinfo=idaapi.tinfo_t(),
        px_word_tinfo=idaapi.tinfo_t(),
        dummy_func=idaapi.tinfo_t(),
        legal_types=[],
    )
    assert c.ea64 is True
    assert c.ea_size == 8
    assert c.legal_types == []


def test_consts_dataclass_is_mutable() -> None:
    """Consts is a regular dataclass (not frozen) so it can be re-assigned.

    `Session.consts` is a regular attribute that can be replaced when the
    user opens a new IDB.
    """
    c = Consts(
        ea64=False, ea_size=4,
        void_tinfo=idaapi.tinfo_t(), pvoid_tinfo=idaapi.tinfo_t(),
        const_void_tinfo=idaapi.tinfo_t(), const_pvoid_tinfo=idaapi.tinfo_t(),
        char_tinfo=idaapi.tinfo_t(), pchar_tinfo=idaapi.tinfo_t(),
        const_pchar_tinfo=idaapi.tinfo_t(),
        byte_tinfo=idaapi.tinfo_t(), pbyte_tinfo=idaapi.tinfo_t(),
        word_tinfo=idaapi.tinfo_t(), pword_tinfo=idaapi.tinfo_t(),
        x_word_tinfo=idaapi.tinfo_t(), px_word_tinfo=idaapi.tinfo_t(),
        dummy_func=idaapi.tinfo_t(), legal_types=[],
    )
    c.ea64 = True
    c.ea_size = 8
    assert c.ea64 is True
    assert c.ea_size == 8


# --- init_consts factory ------------------------------------------------------


def test_init_consts_returns_consts() -> None:
    """init_consts() returns a Consts instance."""
    c = init_consts()
    assert isinstance(c, Consts)


def test_init_consts_populates_all_tinfo_fields() -> None:
    """Every tinfo field is non-None after init_consts()."""
    c = init_consts()
    tinfo_fields = [
        "void_tinfo", "pvoid_tinfo", "const_void_tinfo", "const_pvoid_tinfo",
        "char_tinfo", "pchar_tinfo", "const_pchar_tinfo",
        "byte_tinfo", "pbyte_tinfo",
        "word_tinfo", "pword_tinfo",
        "x_word_tinfo", "px_word_tinfo",
        "dummy_func",
    ]
    for fname in tinfo_fields:
        value = getattr(c, fname)
        # Under mock_ida, idaapi.tinfo_t() returns a MagicMock — must not be
        # Python None. Real IDA returns a usable tinfo_t instance.
        assert value is not None, f"{fname} should be populated"


def test_init_consts_legal_types_has_5_entries() -> None:
    """LEGAL_TYPES is exactly [PVOID, PX_WORD, PWORD, PBYTE, X_WORD]."""
    c = init_consts()
    assert len(c.legal_types) == 5


def test_init_consts_ea_size_matches_ea64() -> None:
    """ea_size is 8 if ea64, else 4."""
    c = init_consts()
    if c.ea64:
        assert c.ea_size == 8
    else:
        assert c.ea_size == 4


# --- Session integration -----------------------------------------------------


def test_session_consts_default_is_none() -> None:
    """A fresh Session has consts=None (not yet opened)."""
    s = Session()
    assert s.consts is None


def test_session_open_populates_consts() -> None:
    """Session.open() calls init_consts() and stores the result."""
    s = Session()
    assert s.consts is None
    s.open()
    assert s.consts is not None
    assert isinstance(s.consts, Consts)


def test_session_open_is_idempotent_for_consts() -> None:
    """Calling open() twice does not re-init consts (idempotent guard)."""
    s = Session()
    s.open()
    first_consts = s.consts
    s.open()  # should not error
    assert s.consts is first_consts  # same instance — not re-created


def test_session_close_keeps_consts() -> None:
    """close() does not clear consts (re-open would re-init anyway)."""
    s = Session()
    s.open()
    saved = s.consts
    s.close()
    assert s.consts is saved
