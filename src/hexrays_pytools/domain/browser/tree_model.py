"""TreeModel for the class browser (Class > VTable > VirtualMethod).

Replaces the Qt model portion of `core/classes.py:TreeModel`. Uses stdlib
`re.search` (was `QRegExp.indexIn` which is removed in Qt6).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import idaapi  # type: ignore[import-not-found]
from PySide6 import QtCore

from .registered_class import Class

# Sentinel "invalid" index. B008 forbids calling QtCore.QModelIndex() in a
# default-argument expression; hold it in a module-level singleton instead.
_INVALID_INDEX: QtCore.QModelIndex = QtCore.QModelIndex()


@dataclass
class TreeItem:
    """A single node in the class tree (Class, RegisteredVTable, or VirtualMethod)."""

    item: Any
    parent: TreeItem | None = None
    children: list[TreeItem] = field(default_factory=list)

    def append_child(self, child: TreeItem) -> None:
        self.children.append(child)
        child.parent = self

    def child(self, row: int) -> TreeItem | None:
        if 0 <= row < len(self.children):
            return self.children[row]
        return None

    def row(self) -> int:
        if self.parent is not None:
            return self.parent.children.index(self)
        return 0


class TreeModel(QtCore.QAbstractItemModel):
    """Qt tree model for the class browser.

    Columns: Name, Declaration, Address.
    Hierarchy: Class -> RegisteredVTable -> VirtualMethod.
    """

    HEADERS = ["Name", "Declaration", "Address"]

    def __init__(self) -> None:
        super().__init__()
        self.root_item: TreeItem = TreeItem(item=None)
        self._classes: dict[str, Class] = {}

    def rowCount(  # noqa: N802 - Qt API override
        self,
        parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex = _INVALID_INDEX,
    ) -> int:
        if parent.column() > 0:
            return 0
        item = self._item_from_index(parent) if parent.isValid() else self.root_item
        return len(item.children)

    def columnCount(  # noqa: N802 - Qt API override
        self,
        parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex = _INVALID_INDEX,
    ) -> int:
        return len(self.HEADERS)

    def headerData(  # noqa: N802 - Qt API override
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole and orientation == QtCore.Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None

    def data(  # noqa: N802 - Qt API override
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None
        tree_item = self._item_from_index(index)
        node = tree_item.item
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            col = index.column()
            if col == 0:
                return getattr(node, "name", "")
            if col == 1:
                return getattr(node, "tooltip", lambda: "")() if hasattr(node, "tooltip") else ""
            if col == 2:
                addr = getattr(node, "address", 0) or getattr(node, "ordinal", 0)
                return hex(int(addr))
        return None

    def index(  # noqa: N802 - Qt API override
        self,
        row: int,
        column: int,
        parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex = _INVALID_INDEX,
    ) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        parent_item = self._item_from_index(parent) if parent.isValid() else self.root_item
        child_item = parent_item.child(row)
        if child_item is not None:
            return self.createIndex(row, column, child_item)
        return QtCore.QModelIndex()

    def parent(  # type: ignore[override]  # noqa: N802 - Qt API override
        # PySide6 stubs overload QObject.parent() -> QObject and
        # QAbstractItemModel.parent(index) -> QModelIndex; a single Python
        # override cannot satisfy both. This matches the legacy Qt signature.
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        /,
    ) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()
        child_item = self._item_from_index(index)
        parent_item = child_item.parent
        if parent_item is None or parent_item is self.root_item:
            return QtCore.QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def _item_from_index(
        self, index: QtCore.QModelIndex | QtCore.QPersistentModelIndex
    ) -> TreeItem:
        if not index.isValid():
            return self.root_item
        ptr = index.internalPointer()
        return ptr if isinstance(ptr, TreeItem) else self.root_item

    def setupModelData(self) -> None:  # noqa: N802 - Qt API naming
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
            for _offset, vtable in cls.vtables.items():
                vt_item = TreeItem(item=vtable)
                class_item.append_child(vt_item)
                # VirtualMethod nodes
                for vf in vtable.virtual_functions:
                    vf_item = TreeItem(item=vf)
                    vt_item.append_child(vf_item)
        self.endResetModel()

    def has_function_match(self, class_name: str, name_regex: str) -> bool:
        """Return True if any class has a function matching ``name_regex``.

        FIX B2: was ``QRegExp.indexIn``; now stdlib :func:`re.search`.
        """
        _ = class_name  # reserved for future per-class filtering; current impl scans all
        for cls in self._classes.values():
            for vtable in cls.vtables.values():
                for vf in getattr(vtable, "virtual_functions", []):
                    if re.search(name_regex, getattr(vf, "name", "")):
                        return True
        return False
