"""Test TreeModel with Qt offscreen."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock

from hexrays_pytools.domain.browser.tree_model import TreeItem, TreeModel


def test_tree_item_init() -> None:
    item = TreeItem(item=None)
    assert item.children == []
    assert item.parent is None


def test_tree_item_append_child() -> None:
    parent = TreeItem(item=None)
    child = TreeItem(item="child")
    parent.append_child(child)
    assert len(parent.children) == 1
    assert child.parent is parent


def test_tree_model_init_empty() -> None:
    m = TreeModel()
    assert m.rowCount() == 0
    assert m.columnCount() == 3


def test_tree_model_header() -> None:
    m = TreeModel()
    from PySide6 import QtCore
    assert m.headerData(0, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole) == "Name"
    assert m.headerData(1, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole) == "Declaration"
    assert m.headerData(2, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole) == "Address"


def test_has_function_match_with_re() -> None:
    """has_function_match uses stdlib re.search (B2 fix)."""
    m = TreeModel()
    vf = MagicMock()
    vf.name = "doSomething"
    vt = MagicMock()
    vt.virtual_functions = [vf]
    cls = MagicMock()
    cls.name = "Foo"
    cls.vtables = {0: vt}
    m._classes = {"Foo": cls}
    assert m.has_function_match("Foo", r"doSome") is True
    assert m.has_function_match("Foo", r"nope") is False
