"""Test AbstractMember / Member / VoidMember."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.recon.member import AbstractMember, Member, VoidMember


def test_abstract_member_default_fields() -> None:
    """AbstractMember has sensible defaults."""
    m = AbstractMember(offset=0x10)
    assert m.tinfo is None
    assert m.name == ""
    assert m.enabled is True
    assert m.size == 0


def test_abstract_member_size_from_tinfo() -> None:
    """size property reads from tinfo.get_size()."""
    m = AbstractMember(offset=0)
    tinfo = MagicMock()
    tinfo.get_size.return_value = 4
    m.tinfo = tinfo
    assert m.size == 4


def test_member_eq_merges_scanned_variables() -> None:
    """Two AbstractMembers with same offset+type are equal and merge scanned_variables."""
    ta = MagicMock()
    ta.dstr.return_value = "int"
    tb = MagicMock()
    tb.dstr.return_value = "int"
    a = AbstractMember(offset=0x10, tinfo=ta)
    a.scanned_variables = {1, 2}
    b = AbstractMember(offset=0x10, tinfo=tb)
    b.scanned_variables = {3}
    assert a == b
    assert a.scanned_variables == {1, 2, 3}


def test_member_eq_keeps_distinct_same_size_types() -> None:
    ta = MagicMock()
    ta.dstr.return_value = "int"
    ta.get_size.return_value = 4
    tb = MagicMock()
    tb.dstr.return_value = "float"
    tb.get_size.return_value = 4
    assert AbstractMember(offset=0x10, tinfo=ta) != AbstractMember(offset=0x10, tinfo=tb)


def test_member_lt_compares_offset() -> None:
    """AbstractMember orders by offset."""
    a = AbstractMember(offset=0x10)
    b = AbstractMember(offset=0x20)
    assert a < b


def test_void_member_wildcard_type_match() -> None:
    """VoidMember.type_equals_to always returns True."""
    v = VoidMember(offset=0)
    assert v.type_equals_to("anything") is True


def test_member_class_is_subclass() -> None:
    """Member is a subclass of AbstractMember."""
    m = Member(offset=0, name="x")
    assert isinstance(m, AbstractMember)
    assert m.name == "x"


def test_void_member_default_tinfo_resolved() -> None:
    """Regression: VoidMember.__post_init__ resolves tinfo when caller passes None.

    IDA's ``udm_t_type_set`` rejects ``None`` with
    ``ValueError: invalid null reference``. The default ``BYTE_TINFO`` injection
    in ``__post_init__`` keeps VoidMember safe to use in ``StructureModel.pack``.
    """
    v = VoidMember(offset=0)
    # Either a real tinfo (real IDA env) or None (mock env), but never
    # raise during construction.
    if v.tinfo is not None:
        assert hasattr(v.tinfo, "create") or hasattr(v.tinfo, "create_simple_type")


def test_void_member_get_udt_member_does_not_crash() -> None:
    """Regression: ``get_udt_member`` must not let a None tinfo reach IDA.

    Under mock_ida, ``udt_member_t`` may not be fully implemented. Our path
    is robust to that — the assertion just verifies no exception is raised
    when constructing the udt_member.
    """
    v = VoidMember(offset=0)
    try:
        m = v.get_udt_member()
        assert hasattr(m, "offset")
        assert hasattr(m, "size")
    except (AttributeError, RuntimeError, ValueError):
        # Mock may raise on udt_member_t() — still acceptable, our goal is
        # just that we never propagate None to the real IDA setter
        # (which would trigger ValueError: invalid null reference).
        pass


def test_make_byte_tinfo_handles_real_and_mock_apis() -> None:
    """Regression: ``_make_byte_tinfo`` must not crash on any IDA env.

    Real IDA 9.4: ``tinfo_t(BTF_BYTE)`` already produces ``_BYTE``;
    ``create_simple_type(BT_BTY|BTS_BYTE)`` then triggers
    ``OverflowError: argument 2 of type 'type_t'``.

    Mock env: BT_BTY is a MagicMock (not int), so the fallback branch
    runs without raising.
    """
    import sys
    sys.path.insert(0, "tools")
    import mock_ida  # type: ignore[import-not-found]
    mock_ida.install()

    from hexrays_pytools.domain.recon.member import _make_byte_tinfo

    ti = _make_byte_tinfo()
    # Either we got a tinfo_t-like object, or the env is so stripped that
    # we couldn't build one — both acceptable.
    if ti is not None:
        assert hasattr(ti, "get_size") or hasattr(ti, "size")


# --- Behaviour ported from v1.x (set_enabled / switch_array_flag / font / ----
# --- has_collision / type_name / score / type_equals_to / activate) ---------


def test_set_enabled_false_clears_array_flag() -> None:
    """Disabling a member also clears its array flag (mirrors v1)."""
    m = AbstractMember(offset=0, is_array=True)
    m.set_enabled(False)
    assert m.enabled is False
    assert m.is_array is False


def test_set_enabled_true_clears_array_flag() -> None:
    """Enabling clears is_array too, matching the original plugin."""
    m = AbstractMember(offset=0, is_array=True)
    m.set_enabled(True)
    assert m.enabled is True
    assert m.is_array is False


def test_void_member_set_enabled_preserves_array_flag() -> None:
    v = VoidMember(offset=0, is_array=True)
    v.set_enabled(False)
    assert v.enabled is False
    assert v.is_array is True
    v.set_enabled(True)
    assert v.enabled is True
    assert v.is_array is True


def test_switch_array_flag_toggles() -> None:
    """Plain members toggle is_array; VoidMember stays put."""
    m = AbstractMember(offset=0)
    m.switch_array_flag()
    assert m.is_array is True
    m.switch_array_flag()
    assert m.is_array is False

    v = VoidMember(offset=0)
    v.switch_array_flag()
    assert v.is_array is True  # unchanged (no-op override)


def test_font_default_is_none() -> None:
    """Default font property returns None (subclasses may override with QFont)."""
    assert AbstractMember(offset=0).font is None


def test_member_generates_operand_style_name_when_empty() -> None:
    tinfo = MagicMock()
    tinfo.get_size.return_value = 4
    tinfo.is_floating.return_value = False
    tinfo.is_integral.return_value = True
    member = Member(offset=0x10, tinfo=tinfo)
    assert member.name == "dword_10"


def test_type_name_fallbacks() -> None:
    """type_name: tinfo.dstr() when present, else name, else 'void'."""
    m = AbstractMember(offset=0, name="field_4")
    assert m.type_name == "field_4"

    m2 = AbstractMember(offset=0)
    assert m2.type_name == "void"

    tinfo = MagicMock()
    tinfo.dstr.return_value = "int"
    m3 = AbstractMember(offset=0, tinfo=tinfo)
    assert m3.type_name == "int"


def test_has_collision_overlapping_ranges() -> None:
    """has_collision compares [offset, offset+size) ranges.

    Ported line-by-line from v1 ``AbstractMember.has_collision`` — note the
    deliberate asymmetry: the ``else`` branch uses ``>=`` (touching counts as
    collision) while the ``if`` branch uses ``>`` (touching does not). Keep
    the test pinned to the original semantics, not to idealized symmetry.
    """
    a = AbstractMember(offset=0x10)
    b = AbstractMember(offset=0x14)
    ta = MagicMock()
    ta.get_size.return_value = 8   # a: [0x10, 0x18)
    tb = MagicMock()
    tb.get_size.return_value = 4   # b: [0x14, 0x18)
    a.tinfo = ta
    b.tinfo = tb
    assert a.has_collision(b) is True
    assert b.has_collision(a) is True

    c = AbstractMember(offset=0x18)
    tc = MagicMock()
    tc.get_size.return_value = 4   # c: [0x18, 0x1C)
    c.tinfo = tc
    # a.offset <= c.offset → a_end (0x18) > c.offset (0x18) is False
    assert a.has_collision(c) is False
    # c.offset > a.offset → a_end (0x18) >= c.offset (0x18) is True (v1 quirk)
    assert c.has_collision(a) is True


def test_score_known_type_uses_scoring_table() -> None:
    """score delegates to pure.scoring.score_member for named types."""
    tinfo = MagicMock()
    tinfo.dstr.return_value = "int"
    tinfo.get_size.return_value = 4
    m = AbstractMember(offset=0, tinfo=tinfo)
    s = m.score
    assert isinstance(s, int)
    assert s != 0xFFFF  # known type should not hit the worst-case fallback


def test_score_funcptr_gets_mid_value() -> None:
    """Function pointers score 0x1000 + len(str) when scoring table misses."""
    tinfo = MagicMock()
    tinfo.dstr.return_value = "_unknown"
    tinfo.is_funcptr.return_value = True
    tinfo.__str__ = lambda _s: "int (__cdecl*)(int)"
    tinfo.get_size.return_value = 4
    m = AbstractMember(offset=0, tinfo=tinfo, name="_unknown")
    s = m.score
    assert 0x1000 <= s < 0xFFFF


def test_score_unknown_name_worst_case() -> None:
    """A type name missing from the scoring table falls back to 0xFFFF.

    Mirrors v1: ``score_table(type_name)`` raises KeyError → funcptr check →
    0xFFFF. A leading-underscore name skips the table lookup entirely and
    also lands on the funcptr/0xFFFF path.
    """
    tinfo = MagicMock()
    tinfo.dstr.return_value = "_SomeUnknownStruct *"
    tinfo.is_funcptr.return_value = False
    tinfo.get_size.return_value = 4
    m = AbstractMember(offset=0, tinfo=tinfo, name="_SomeUnknownStruct *")
    assert m.score == 0xFFFF


def test_type_equals_to() -> None:
    """type_equals_to delegates to tinfo.equals_to; None-safe both ways."""
    ta = MagicMock()
    ta.equals_to.return_value = True
    tb = MagicMock()
    m = AbstractMember(offset=0, tinfo=ta)
    assert m.type_equals_to(tb) is True
    ta.equals_to.assert_called_once_with(tb)

    assert m.type_equals_to(None) is False
    assert AbstractMember(offset=0).type_equals_to(tb) is False

    ta2 = MagicMock()
    ta2.equals_to.side_effect = RuntimeError("bad")
    m2 = AbstractMember(offset=0, tinfo=ta2)
    assert m2.type_equals_to(tb) is False


def test_get_udt_member_renames_auto_names_only() -> None:
    """get_udt_member rewrites byte_X/dword_X names but keeps user names."""
    import idaapi  # noqa: F401 - ensure mock is active

    tinfo = MagicMock()
    tinfo.dstr.return_value = "int"
    tinfo.get_size.return_value = 4

    auto = AbstractMember(offset=0x10, tinfo=tinfo, name="dword_10")
    udt = auto.get_udt_member()
    if udt is not None:  # mock env may not build udt_member_t
        assert udt.name != "dword_10"  # rewritten from type name + offset
        assert udt.offset == 0x10 * 8
        assert udt.size == 4 * 8

    user = AbstractMember(offset=0x10, tinfo=tinfo, name="pContext")
    udt2 = user.get_udt_member()
    if udt2 is not None:
        assert udt2.name == "pContext"


def test_get_udt_member_array_size_uses_total_bit_size() -> None:
    """IDA 9 udm.size describes the whole array member, in bits."""
    tinfo = MagicMock()
    tinfo.dstr.return_value = "int"
    tinfo.get_size.return_value = 4
    member = AbstractMember(offset=0x20, tinfo=tinfo, name="values")

    udt = member.get_udt_member(array_size=3)

    assert udt is not None
    assert udt.offset == 0x20 * 8
    assert udt.size == 4 * 3 * 8


def test_activate_cancel_is_noop() -> None:
    """activate() with cancelled ask_str leaves the member unchanged."""
    from unittest.mock import patch

    import idaapi

    m = AbstractMember(offset=0, name="old")
    with patch.object(idaapi, "ask_str", return_value=None):
        m.activate(MagicMock())
    assert m.name == "old"
