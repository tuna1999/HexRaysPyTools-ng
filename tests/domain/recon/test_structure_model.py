"""Test StructureModel with Qt offscreen platform."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock

from hexrays_pytools.domain.recon.member import AbstractMember
from hexrays_pytools.domain.recon.structure_model import StructureModel


def test_model_init_empty() -> None:
    m = StructureModel()
    assert m.rowCount() == 0
    assert m.columnCount() == 5


def test_model_header_data() -> None:
    m = StructureModel()
    from PySide6 import QtCore

    assert m.headerData(0, QtCore.Qt.Orientation.Horizontal, QtCore.Qt.ItemDataRole.DisplayRole) == "Offset"
    assert m.headerData(1, QtCore.Qt.Orientation.Horizontal, QtCore.Qt.ItemDataRole.DisplayRole) == "Name"
    assert m.headerData(2, QtCore.Qt.Orientation.Horizontal, QtCore.Qt.ItemDataRole.DisplayRole) == "Type"


def test_model_with_items() -> None:
    item = AbstractMember(offset=0x10, name="foo")
    item.tinfo = MagicMock()
    item.tinfo.get_size.return_value = 4
    m = StructureModel(items=[item])
    assert m.rowCount() == 1
    assert m.columnCount() == 5


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
    """data() returns correct values for each column under DisplayRole."""
    from PySide6 import QtCore

    item = AbstractMember(offset=0x10, name="foo")
    item.tinfo = MagicMock()
    item.tinfo.get_size.return_value = 4
    m = StructureModel(items=[item])
    idx = m.index(0, 0, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.DisplayRole) == "0x10"
    idx = m.index(0, 1, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.DisplayRole) == "foo"
    idx = m.index(0, 2, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.DisplayRole) is not None  # str(tinfo)
    idx = m.index(0, 3, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.DisplayRole) == 4
    idx = m.index(0, 4, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.DisplayRole) is True


def test_model_data_invalid_index() -> None:
    """data() returns None for an invalid index."""
    from PySide6 import QtCore

    m = StructureModel()
    invalid_idx = QtCore.QModelIndex()
    assert m.data(invalid_idx, QtCore.Qt.DisplayRole) is None


def test_model_data_non_display_role() -> None:
    """data() returns None for a non-DisplayRole."""
    from PySide6 import QtCore

    m = StructureModel(items=[AbstractMember(offset=0, name="x")])
    idx = m.index(0, 0, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.EditRole) is None


def test_model_data_row_out_of_range() -> None:
    """data() returns None when row index exceeds item count."""
    from PySide6 import QtCore

    m = StructureModel(items=[AbstractMember(offset=0, name="x")])
    # Forge an index pointing at row 5 (only 1 item present).
    idx = m.createIndex(5, 0, None)
    assert m.data(idx, QtCore.Qt.DisplayRole) is None


def test_model_data_type_column_without_tinfo() -> None:
    """data() returns '' for Type column when item.tinfo is None."""
    from PySide6 import QtCore

    m = StructureModel(items=[AbstractMember(offset=0, name="x", tinfo=None)])
    idx = m.index(0, 2, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.DisplayRole) == ""


def test_model_data_size_column_without_tinfo() -> None:
    """data() Size column returns 0 when tinfo is None (via size property)."""
    from PySide6 import QtCore

    m = StructureModel(items=[AbstractMember(offset=0, name="x", tinfo=None)])
    idx = m.index(0, 3, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.DisplayRole) == 0


def test_model_data_disabled_item() -> None:
    """data() Enabled column reflects item.enabled=False."""
    from PySide6 import QtCore

    m = StructureModel(items=[AbstractMember(offset=0, name="x", enabled=False)])
    idx = m.index(0, 4, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.DisplayRole) is False


def test_model_items_property_returns_copy() -> None:
    """items property returns a fresh list copy."""
    a = AbstractMember(offset=0x10, name="a")
    m = StructureModel(items=[a])
    snapshot = m.items
    snapshot.append(AbstractMember(offset=0x20, name="b"))
    assert len(m.items) == 1
