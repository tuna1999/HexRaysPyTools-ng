# Task 3.3 Brief: domain/browser/tree_model.py

## Files (2)
1. `src/hexrays_pytools/domain/browser/tree_model.py`
2. `tests/domain/browser/test_tree_model.py`

## `tree_model.py` (verbatim — fixes B2: QRegExp.indexIn → re.search)

```python
"""TreeModel for the class browser (Class > VTable > VirtualMethod).

Replaces the Qt model portion of `core/classes.py:TreeModel`. Uses stdlib
`re.search` (was `QRegExp.indexIn` which is removed in Qt6).
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any

import idaapi  # type: ignore[import-not-found]
from PySide6 import QtCore  # type: ignore[import-not-found]

from .registered_class import Class
from .registered_vtable import RegisteredVTable, VirtualMethod


@dataclass
class TreeItem:
    """A single node in the class tree."""
    item: Any  # Class, RegisteredVTable, or VirtualMethod
    parent: "TreeItem | None" = None
    children: list = field(default_factory=list)

    def append_child(self, child: "TreeItem") -> None:
        self.children.append(child)
        child.parent = self

    def child(self, row: int) -> "TreeItem | None":
        if 0 <= row < len(self.children):
            return self.children[row]
        return None

    def row(self) -> int:
        if self.parent is not None:
            return self.parent.children.index(self)
        return 0


class TreeModel(QtCore.QAbstractItemModel):
    """Qt tree model for the class browser."""

    HEADERS = ["Name", "Declaration", "Address"]

    def __init__(self) -> None:
        super().__init__()
        self.root_item = TreeItem(item=None)
        self._classes: dict = {}

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if parent.column() > 0:
            return 0
        item = self._item_from_index(parent) if parent.isValid() else self.root_item
        return len(item.children)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.DisplayRole) -> Any:
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        tree_item = self._item_from_index(index)
        node = tree_item.item
        if role == QtCore.Qt.DisplayRole:
            col = index.column()
            if col == 0:
                return getattr(node, "name", "")
            if col == 1:
                return getattr(node, "tooltip", lambda: "")() if hasattr(node, "tooltip") else ""
            if col == 2:
                addr = getattr(node, "address", 0) or getattr(node, "ordinal", 0)
                return hex(int(addr))
        return None

    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        parent_item = self._item_from_index(parent) if parent.isValid() else self.root_item
        child_item = parent_item.child(row)
        if child_item is not None:
            return self.createIndex(row, column, child_item)
        return QtCore.QModelIndex()

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()
        child_item = self._item_from_index(index)
        parent_item = child_item.parent
        if parent_item is None or parent_item is self.root_item:
            return QtCore.QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def _item_from_index(self, index: QtCore.QModelIndex) -> TreeItem:
        if not index.isValid():
            return self.root_item
        return index.internalPointer()

    def setupModelData(self) -> None:
        """Populate the tree from Local Types (Class nodes with vtables)."""
        self.beginResetModel()
        self.root_item = TreeItem(item=None)
        self._classes = {}
        for ordinal in range(1, int(idaapi.get_ordinal_count())):
            cls = Class.create(int(ordinal))
            if cls is None:
                continue
            self._classes[cls.name] = cls
            class_item = TreeItem(item=cls)
            self.root_item.append_child(class_item)
            # VTable nodes
            for offset, vtable in cls.vtables.items():
                vt_item = TreeItem(item=vtable)
                class_item.append_child(vt_item)
                # VirtualMethod nodes
                for vf in vtable.virtual_functions:
                    vf_item = TreeItem(item=vf)
                    vt_item.append_child(vf_item)
        self.endResetModel()

    def has_function_match(self, class_name: str, name_regex: str) -> bool:
        """Return True if any class has a function matching name_regex.

        FIX B2: was `QRegExp.indexIn`; now stdlib `re.search`.
        """
        for cls in self._classes.values():
            for vtable in cls.vtables.values():
                for vf in getattr(vtable, "virtual_functions", []):
                    if re.search(name_regex, getattr(vf, "name", "")):
                        return True
        return False
```

## `test_tree_model.py` (verbatim)

```python
"""Test TreeModel with Qt offscreen."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from hexrays_pytools.domain.browser.tree_model import TreeModel, TreeItem


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
```

Add `from unittest.mock import MagicMock` to imports.

## Verification
```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=src pytest tests/domain/browser/test_tree_model.py -v
python -m mypy --strict src/hexrays_pytools/domain/browser/tree_model.py
python -m ruff check src/hexrays_pytools/domain/browser/tree_model.py tests/domain/browser/test_tree_model.py
```

## Commit
```bash
git add src/hexrays_pytools/domain/browser/tree_model.py tests/domain/browser/test_tree_model.py
git commit -m "feat(browser): add TreeModel (B2 fix: QRegExp.indexIn → re.search)"
```

## Report
`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-3.3-report.md`