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
    refreshed = QtCore.Signal()

    def __init__(self, demangled_names: dict[str, set[int]] | None = None) -> None:
        super().__init__()
        self.root_item: TreeItem = TreeItem(item=None)
        self._classes: dict[str, Class] = {}
        self._demangled_names = demangled_names or {}
        self.setupModelData()

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
        if role in (QtCore.Qt.ItemDataRole.DisplayRole, QtCore.Qt.ItemDataRole.EditRole):
            getter = getattr(node, "data", None)
            if getter is not None:
                return getter(index.column())
            col = index.column()
            if col == 0:
                return getattr(node, "name", "")
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            font = getattr(node, "font", None)
            if font is not None:
                return font(index.column()) if callable(font) else font
        elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
            tooltip = getattr(node, "tooltip", None)
            if tooltip is not None:
                return tooltip() if callable(tooltip) else tooltip
        elif role == QtCore.Qt.ItemDataRole.BackgroundRole:
            return getattr(node, "color", None)
        elif role == QtCore.Qt.ItemDataRole.ForegroundRole:
            from PySide6 import QtGui

            return QtGui.QBrush(QtGui.QColor("#191919"))
        return None

    def flags(self, index: QtCore.QModelIndex | QtCore.QPersistentModelIndex) -> QtCore.Qt.ItemFlag:
        if not index.isValid():
            return QtCore.Qt.ItemFlag.NoItemFlags
        node = self._item_from_index(index).item
        if hasattr(node, "flags"):
            return node.flags(index.column())
        return super().flags(index)

    def setData(  # noqa: N802 - Qt API override
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        value: Any,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        if role != QtCore.Qt.ItemDataRole.EditRole or not index.isValid() or not value:
            return False
        node = self._item_from_index(index).item
        setter = getattr(node, "setData", None)
        if setter is None:
            return False
        changed = bool(setter(index.column(), str(value)))
        if changed:
            self.dataChanged.emit(index, index)
        return changed

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
            cls = Class.create(int(ordinal), self._demangled_names)
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

    def refresh(self) -> None:
        self.setupModelData()
        refreshed = getattr(self, "refreshed", None)
        if refreshed is not None:
            refreshed.emit()

    def rollback(self) -> None:
        # Rebuild from Local Types so every TreeItem points at the fresh
        # Class/VTable/VirtualMethod objects. Updating Class.vtables in place
        # while keeping the old TreeItems would leave stale child nodes visible.
        self.setupModelData()

    def commit(self) -> None:
        for cls in self._classes.values():
            cls.update_local_type()

    def set_first_argument_type(self, indexes: list[QtCore.QModelIndex]) -> None:
        indexes = [idx for idx in indexes if idx.isValid() and idx.column() == 0]
        if not indexes:
            return
        nodes = [self._item_from_index(idx).item for idx in indexes]
        class_name = nodes[0].name if isinstance(nodes[0], Class) else getattr(nodes[0], "class_name", None)
        if not class_name:
            parent = self._item_from_index(indexes[0]).parent
            while parent is not None and parent is not self.root_item:
                if isinstance(parent.item, Class):
                    class_name = parent.item.name
                    break
                parent = parent.parent
        if not class_name and self._classes:
            class_name = next(iter(self._classes))
        if not class_name:
            return
        for node in nodes:
            setter = getattr(node, "set_first_argument_type", None)
            if setter is not None:
                setter(class_name)

    def open_function(self, index: QtCore.QModelIndex) -> None:
        if not index.isValid():
            return
        node = self._item_from_index(index).item
        opener = getattr(node, "open_function", None)
        if opener is not None:
            opener()

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
