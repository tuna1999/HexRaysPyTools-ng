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
