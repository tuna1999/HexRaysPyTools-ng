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


def test_get_recognized_shape_builds_udt_from_items() -> None:
    """get_recognized_shape returns a tinfo for a non-empty model."""
    m = StructureModel()
    m.add_row(AbstractMember(offset=0, name="a", tinfo=MagicMock(name="int_t")))
    m.add_row(AbstractMember(offset=4, name="b", tinfo=MagicMock(name="int_t")))
    tinfo = m.get_recognized_shape()
    assert tinfo is not None


def test_get_recognized_shape_ignores_disabled_items() -> None:
    """Disabled items are not included in the shape."""
    m = StructureModel()
    m.add_row(AbstractMember(offset=0, name="a", tinfo=MagicMock(name="int_t")))
    second = AbstractMember(offset=4, name="b", tinfo=MagicMock(name="int_t"))
    m.add_row(second)
    second.enabled = False
    tinfo = m.get_recognized_shape()
    assert tinfo is not None


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


def test_calculate_array_size_for_consecutive_same_type() -> None:
    """Two enabled same-type items at consecutive offsets count as an array."""
    a = AbstractMember(offset=0, name="a")
    a.tinfo = MagicMock()
    a.tinfo.get_size.return_value = 4
    a.tinfo.dstr.return_value = "int"
    b = AbstractMember(offset=4, name="b")
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
    m = StructureModel(items=[a])
    # Same offset + same size = match per __eq__
    probe = AbstractMember(offset=0x10, name="b")
    probe.tinfo = MagicMock()
    probe.tinfo.get_size.return_value = 4
    assert m.have_member(probe) is True


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
