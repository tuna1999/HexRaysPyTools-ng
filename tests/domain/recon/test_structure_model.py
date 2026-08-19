"""Test StructureModel with Qt offscreen platform.

Mirrors the original ``TemporaryStructureModel`` layout (4 columns:
Offset, Type, Name, Comment) from
``refs/HexRaysPyTools/HexRaysPyTools/core/temporary_structure.py``.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock

from hexrays_pytools.domain.recon.member import AbstractMember
from hexrays_pytools.domain.recon.structure_model import StructureModel


def test_model_init_empty() -> None:
    m = StructureModel()
    assert m.rowCount() == 0
    assert m.columnCount() == 4


def test_model_header_data() -> None:
    m = StructureModel()
    from PySide6 import QtCore

    assert m.headerData(0, QtCore.Qt.Orientation.Horizontal, QtCore.Qt.ItemDataRole.DisplayRole) == "Offset"
    assert m.headerData(1, QtCore.Qt.Orientation.Horizontal, QtCore.Qt.ItemDataRole.DisplayRole) == "Type"
    assert m.headerData(2, QtCore.Qt.Orientation.Horizontal, QtCore.Qt.ItemDataRole.DisplayRole) == "Name"
    assert m.headerData(3, QtCore.Qt.Orientation.Horizontal, QtCore.Qt.ItemDataRole.DisplayRole) == "Comment"


def test_model_with_items() -> None:
    item = AbstractMember(offset=0x10, name="foo")
    item.tinfo = MagicMock()
    item.tinfo.get_size.return_value = 4
    m = StructureModel(items=[item])
    assert m.rowCount() == 1
    assert m.columnCount() == 4


def test_model_add_row_inserts_sorted() -> None:
    m = StructureModel()
    a = AbstractMember(offset=0x20, name="b")
    b = AbstractMember(offset=0x10, name="a")
    m.add_row(a)
    m.add_row(b)
    assert m.items[0].offset == 0x10
    assert m.items[1].offset == 0x20


def test_model_clear() -> None:
    m = StructureModel()
    m.add_row(AbstractMember(offset=0x10))
    m.clear()
    assert m.rowCount() == 0


def test_model_data_display_role() -> None:
    """data() returns correct values for each column under DisplayRole.

    Columns: 0=Offset (hex+dec), 1=Type, 2=Name, 3=Comment.
    """
    from PySide6 import QtCore

    item = AbstractMember(offset=0x10, name="foo", cmt="hi")
    item.tinfo = MagicMock()
    item.tinfo.get_size.return_value = 4
    item.tinfo.dstr.return_value = "int"
    m = StructureModel(items=[item])
    idx = m.index(0, 0, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.ItemDataRole.DisplayRole) == "0x0010 [16]"
    idx = m.index(0, 1, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.ItemDataRole.DisplayRole) == "int"
    idx = m.index(0, 2, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.ItemDataRole.DisplayRole) == "foo"
    idx = m.index(0, 3, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.ItemDataRole.DisplayRole) == "hi"


def test_model_data_invalid_index() -> None:
    """data() returns None for an invalid index."""
    from PySide6 import QtCore

    m = StructureModel()
    invalid_idx = QtCore.QModelIndex()
    assert m.data(invalid_idx, QtCore.Qt.ItemDataRole.DisplayRole) is None


def test_model_data_non_display_role() -> None:
    """data() returns None for a non-DisplayRole."""
    from PySide6 import QtCore

    m = StructureModel(items=[AbstractMember(offset=0, name="x")])
    idx = m.index(0, 0, QtCore.QModelIndex())
    # No FontRole role requested for column 0 → None
    assert m.data(idx, QtCore.Qt.ItemDataRole.FontRole) is None


def test_model_data_row_out_of_range() -> None:
    """data() returns None when row index exceeds item count."""
    from PySide6 import QtCore

    m = StructureModel(items=[AbstractMember(offset=0, name="x")])
    # Forge an index pointing at row 5 (only 1 item present).
    idx = m.createIndex(5, 0, None)
    assert m.data(idx, QtCore.Qt.ItemDataRole.DisplayRole) is None


def test_model_data_type_column_without_tinfo() -> None:
    """data() returns the void name for Type column when item.tinfo is None."""
    from PySide6 import QtCore

    m = StructureModel(items=[AbstractMember(offset=0, name="void_item", tinfo=None)])
    idx = m.index(0, 1, QtCore.QModelIndex())
    # AbstractMember.type_name returns name (or "void") when tinfo is None.
    assert m.data(idx, QtCore.Qt.ItemDataRole.DisplayRole) == "void_item"


def test_model_data_disabled_item_background() -> None:
    """Disabled item row gets a gray background brush (not DisplayRole string)."""
    from PySide6 import QtCore

    m = StructureModel(items=[AbstractMember(offset=0, name="x", enabled=False)])
    idx = m.index(0, 0, QtCore.QModelIndex())
    # BackgroundRole for disabled item → QColor (gray).
    assert m.data(idx, QtCore.Qt.ItemDataRole.BackgroundRole) is not None


def test_model_items_property_returns_copy() -> None:
    """items property returns a fresh list copy."""
    a = AbstractMember(offset=0x10, name="a")
    m = StructureModel(items=[a])
    snapshot = m.items
    snapshot.append(AbstractMember(offset=0x20, name="b"))
    assert len(m.items) == 1


def test_get_recognized_shape_empty_model_returns_none() -> None:
    """get_recognized_shape returns None when the model has no items."""
    m = StructureModel()
    assert m.get_recognized_shape() is None


def test_get_recognized_shape_selects_matching_local_type(monkeypatch) -> None:
    """Recognize Shape searches Local Types and returns the selected match."""
    idaapi = __import__("idaapi")
    field_type = MagicMock()
    candidate = MagicMock()
    candidate.get_numbered_type.return_value = True
    candidate.is_udt.return_value = True
    candidate.get_size.return_value = 8
    candidate.dstr.return_value = "KnownStruct"

    field = MagicMock()
    field.offset = 0
    field.type = field_type

    class _Udt(list):
        pass

    udt = _Udt()

    def fill_udt(out) -> bool:
        out.extend([field])
        return True

    candidate.get_udt_details.side_effect = fill_udt
    monkeypatch.setattr(idaapi, "get_ordinal_count", lambda: 2)
    monkeypatch.setattr(idaapi, "tinfo_t", lambda arg=None: candidate if arg is None else arg)
    monkeypatch.setattr(idaapi, "udt_type_data_t", lambda: _Udt())

    from hexrays_pytools.domain import chooser as chooser_mod

    monkeypatch.setattr(chooser_mod.MyChoose, "Show", lambda *_a, **_kw: 0)
    item = AbstractMember(offset=0, name="a", tinfo=MagicMock())
    item.tinfo.equals_to.return_value = True
    item.tinfo.get_size.return_value = 4
    m = StructureModel(items=[item])

    assert m.get_recognized_shape() is candidate


# ------------------------------------------------------------------
# New model operations — ported from original TemporaryStructureModel
# ------------------------------------------------------------------


def test_disable_rows_sets_enabled_false() -> None:
    from PySide6 import QtCore

    m = StructureModel()
    a = AbstractMember(offset=0, name="a")
    b = AbstractMember(offset=4, name="b")
    m.add_row(a)
    m.add_row(b)
    idx0 = m.index(0, 0, QtCore.QModelIndex())
    m.disable_rows([idx0])
    assert a.enabled is False
    assert b.enabled is True


def test_enable_rows_sets_enabled_true() -> None:
    from PySide6 import QtCore

    m = StructureModel()
    a = AbstractMember(offset=0, name="a", enabled=False)
    m.add_row(a)
    idx0 = m.index(0, 0, QtCore.QModelIndex())
    m.enable_rows([idx0])
    assert a.enabled is True


def test_set_origin_updates_main_offset() -> None:
    from PySide6 import QtCore

    m = StructureModel()
    m.add_row(AbstractMember(offset=0, name="a"))
    m.add_row(AbstractMember(offset=8, name="b"))
    idx1 = m.index(1, 0, QtCore.QModelIndex())
    m.set_origin([idx1])
    assert m.main_offset == 8


def test_make_array_toggles_is_array() -> None:
    from PySide6 import QtCore

    m = StructureModel()
    a = AbstractMember(offset=0, name="a")
    m.add_row(a)
    idx0 = m.index(0, 0, QtCore.QModelIndex())
    m.make_array([idx0])
    assert a.is_array is True
    m.make_array([idx0])
    assert a.is_array is False


def test_remove_items_removes_rows() -> None:
    from PySide6 import QtCore

    m = StructureModel()
    m.add_row(AbstractMember(offset=0, name="a"))
    m.add_row(AbstractMember(offset=4, name="b"))
    idx0 = m.index(0, 0, QtCore.QModelIndex())
    m.remove_items([idx0])
    assert m.rowCount() == 1
    assert m.items[0].name == "b"


def test_calculate_array_size_uses_distance_to_next_enabled() -> None:
    """Array length is inferred from next enabled offset, matching v1."""
    a = AbstractMember(offset=0, name="a")
    a.tinfo = MagicMock()
    a.tinfo.get_size.return_value = 4
    a.tinfo.dstr.return_value = "int"
    b = AbstractMember(offset=8, name="b")
    b.tinfo = MagicMock()
    b.tinfo.get_size.return_value = 4
    b.tinfo.dstr.return_value = "int"
    m = StructureModel(items=[a, b])
    assert m.calculate_array_size(0) == 2


def test_get_name_returns_default_when_no_vtable() -> None:
    m = StructureModel()
    m.add_row(AbstractMember(offset=0, name="a"))
    # No vtable, no DEFAULT_STRUCT_NAME → returns None
    assert m.get_name() is None


def test_have_member_returns_true_when_present() -> None:
    a = AbstractMember(offset=0x10, name="a")
    a.tinfo = MagicMock()
    a.tinfo.get_size.return_value = 4
    a.tinfo.dstr.return_value = "int"
    m = StructureModel(items=[a])
    # Same offset + same type = match per upstream __eq__
    probe = AbstractMember(offset=0x10, name="b")
    probe.tinfo = MagicMock()
    probe.tinfo.get_size.return_value = 4
    probe.tinfo.dstr.return_value = "int"
    assert m.have_member(probe) is True


def test_add_row_merges_duplicate_scanned_variables() -> None:
    t1 = MagicMock()
    t1.dstr.return_value = "int"
    t1.get_size.return_value = 4
    t2 = MagicMock()
    t2.dstr.return_value = "int"
    t2.get_size.return_value = 4
    first = AbstractMember(offset=0x10, tinfo=t1, scanned_variables={1})
    duplicate = AbstractMember(offset=0x10, tinfo=t2, scanned_variables={2})
    model = StructureModel(items=[first])

    model.add_row(duplicate)

    assert model.rowCount() == 1
    assert model.items[0].scanned_variables == {1, 2}


def test_get_unique_scanned_variables_filters_by_origin() -> None:
    a = AbstractMember(offset=0, name="a", origin=0)
    b = AbstractMember(offset=4, name="b", origin=8)
    sv_a = MagicMock()
    sv_b = MagicMock()
    a.scanned_variables = {sv_a}
    b.scanned_variables = {sv_b}
    m = StructureModel(items=[a, b])
    assert sv_a in m.get_unique_scanned_variables(0)
    assert sv_b not in m.get_unique_scanned_variables(0)
    assert sv_b in m.get_unique_scanned_variables(8)


def test_pack_substructure_replaces_selected_range(monkeypatch) -> None:
    from PySide6 import QtCore

    a = AbstractMember(offset=0, name="a")
    b = AbstractMember(offset=4, name="b")
    c = AbstractMember(offset=8, name="c")
    model = StructureModel(items=[a, b, c])
    packed_tinfo = MagicMock(name="packed_tinfo")
    monkeypatch.setattr(model, "pack", MagicMock(return_value=packed_tinfo))

    idx0 = model.index(0, 0, QtCore.QModelIndex())
    idx1 = model.index(1, 0, QtCore.QModelIndex())
    model.pack_substructure([idx0, idx1])

    assert len(model.items) == 2
    assert model.items[0].offset == 0
    assert model.items[0].tinfo is packed_tinfo
    assert model.items[1].name == "c"
    model.pack.assert_called_once_with(0, 2)


def test_unpack_substructure_expands_udt_members(monkeypatch) -> None:
    from PySide6 import QtCore

    idaapi = __import__("idaapi")
    nested_tinfo = MagicMock()
    nested_tinfo.is_udt.return_value = True

    u0 = MagicMock()
    u0.offset = 0
    u0.name = "x"
    u0.type = MagicMock()
    u0.cmt = "cx"
    u1 = MagicMock()
    u1.offset = 32
    u1.name = "y"
    u1.type = MagicMock()
    u1.cmt = "cy"

    class _Udt(list):
        pass

    udt = _Udt([u0, u1])
    monkeypatch.setattr(idaapi, "udt_type_data_t", lambda: udt)
    nested_tinfo.get_udt_details.return_value = True
    model = StructureModel(items=[AbstractMember(offset=0x20, tinfo=nested_tinfo, name="nested")])

    idx = model.index(0, 0, QtCore.QModelIndex())
    model.unpack_substructure([idx])

    assert [(x.offset, x.name, x.cmt) for x in model.items] == [
        (0x20, "x", "cx"),
        (0x24, "y", "cy"),
    ]


def test_resolve_types_disables_worse_colliding_candidate() -> None:
    better_tinfo = MagicMock()
    worse_tinfo = MagicMock()
    better_tinfo.get_size.return_value = 4
    worse_tinfo.get_size.return_value = 8

    # Upstream score semantics: larger score wins on collision.
    class _Better(AbstractMember):
        @property
        def score(self) -> int:
            return 10

    class _Worse(AbstractMember):
        @property
        def score(self) -> int:
            return 1

    worse = _Worse(offset=0, tinfo=worse_tinfo, name="worse")
    better = _Better(offset=0, tinfo=better_tinfo, name="better")
    model = StructureModel(items=[worse, better])

    model.resolve_types()

    assert better.enabled is True
    assert worse.enabled is False


def test_load_struct_uses_named_tinfo_and_skips_padding(monkeypatch) -> None:
    idaapi = __import__("idaapi")
    tif = MagicMock()
    tif.get_named_type.return_value = True
    tif.is_udt.return_value = True
    monkeypatch.setattr(idaapi, "tinfo_t", lambda: tif)
    monkeypatch.setattr(idaapi, "ask_str", lambda *_a: "Loaded")

    gap = MagicMock()
    gap.offset = 0
    gap.name = "gap_0"
    gap.type = MagicMock()
    gap.cmt = ""
    field = MagicMock()
    field.offset = 32
    field.name = "field_4"
    field.type = MagicMock()
    field.cmt = "hello"

    class _Udt(list):
        pass

    udt = _Udt([gap, field])
    monkeypatch.setattr(idaapi, "udt_type_data_t", lambda: udt)
    tif.get_udt_details.return_value = True
    model = StructureModel()

    model.load_struct()

    assert [(x.offset, x.name, x.cmt) for x in model.items] == [(4, "field_4", "hello")]
    assert model.default_name == "Loaded"


def test_recognize_shape_single_row_applies_pointer_to_origin_zero(monkeypatch) -> None:
    from PySide6 import QtCore

    idaapi = __import__("idaapi")
    shape = MagicMock()
    ptr = MagicMock()
    monkeypatch.setattr(idaapi, "tinfo_t", lambda: ptr)
    scanned = MagicMock()
    item = AbstractMember(offset=0, name="a", origin=0)
    item.scanned_variables = {scanned}
    model = StructureModel(items=[item])
    monkeypatch.setattr(model, "get_recognized_shape", MagicMock(return_value=shape))

    idx = model.index(0, 0, QtCore.QModelIndex())
    model.recognize_shape([idx])

    ptr.create_ptr.assert_called_once_with(shape)
    scanned.apply_type.assert_called_once_with(ptr)
    assert model.items == []


def test_recognize_shape_range_replaces_covered_members(monkeypatch) -> None:
    from PySide6 import QtCore

    idaapi = __import__("idaapi")
    shape = MagicMock()
    shape.get_size.return_value = 8
    ptr = MagicMock()
    monkeypatch.setattr(idaapi, "tinfo_t", lambda: ptr)
    a = AbstractMember(offset=0x10, name="a", origin=0x10)
    b = AbstractMember(offset=0x14, name="b", origin=0x10)
    c = AbstractMember(offset=0x20, name="c")
    scanned = MagicMock()
    a.scanned_variables = {scanned}
    model = StructureModel(items=[a, b, c])
    monkeypatch.setattr(model, "get_recognized_shape", MagicMock(return_value=shape))

    idx0 = model.index(0, 0, QtCore.QModelIndex())
    idx1 = model.index(1, 0, QtCore.QModelIndex())
    model.recognize_shape([idx0, idx1])

    assert [(x.offset, x.tinfo) for x in model.items] == [(0x10, shape), (0x20, c.tinfo)]
    scanned.apply_type.assert_called_once_with(ptr)


def test_set_decls_parses_and_applies_pointer(monkeypatch) -> None:
    idaapi = __import__("idaapi")
    idaapi.idc_parse_types.return_value = 0
    base = MagicMock(name="base")
    base.get_named_type.return_value = True
    ptr = MagicMock(name="ptr")
    monkeypatch.setattr(idaapi, "tinfo_t", MagicMock(side_effect=[base, ptr]))
    scanned = MagicMock()
    item = AbstractMember(offset=0, origin=0)
    item.scanned_variables = {scanned}
    model = StructureModel(items=[item])

    result = model.set_decls("Vec_int", "struct Vec_int { int x; };")

    assert result is base
    idaapi.idc_parse_types.assert_called_once_with("struct Vec_int { int x; };", 0)
    base.get_named_type.assert_called_once_with(idaapi.get_idati(), "Vec_int")
    ptr.create_ptr.assert_called_once_with(base)
    scanned.apply_type.assert_called_once_with(ptr)


def test_set_stl_type_renders_installs_and_clears(monkeypatch) -> None:
    from hexrays_pytools.pure.result import Result

    tmpl = MagicMock()
    tmpl.get_decl_str.return_value = Result.ok(("Vec_int", "struct Vec_int { int x; };"))
    model = StructureModel(
        items=[AbstractMember(offset=0, name="a")], templated_types=tmpl
    )
    installed = MagicMock()
    monkeypatch.setattr(model, "set_decls", MagicMock(return_value=installed))

    model.set_stl_type("vector", ("int", "values"))

    tmpl.get_decl_str.assert_called_once_with("vector", ["int", "values"])
    model.set_decls.assert_called_once_with("Vec_int", "struct Vec_int { int x; };")
    assert model.items == []
