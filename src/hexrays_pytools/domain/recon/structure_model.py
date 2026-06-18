"""QAbstractTableModel for the Structure Builder widget.

Replaces the Qt model portion of `core/temporary_structure.py:TemporaryStructureModel`.
Uses PySide6. For testing, mocks are provided via `tools/mock_ida.py`.
"""
from __future__ import annotations

import logging
from typing import Any

from PySide6 import QtCore

from .member import AbstractMember

logger = logging.getLogger(__name__)

# Sentinel "invalid" index. B008 forbids calling QtCore.QModelIndex() in a
# default-argument expression; hold it in a module-level singleton instead.
_INVALID_INDEX: QtCore.QModelIndex = QtCore.QModelIndex()


class StructureModel(QtCore.QAbstractTableModel):
    """Qt table model for the structure builder.

    Columns: Offset, Name, Type, Size, Enabled.
    """

    HEADERS = ["Offset", "Name", "Type", "Size", "Enabled"]

    def __init__(self, items: list[Any] | None = None) -> None:
        super().__init__()
        self._items: list[Any] = list(items) if items is not None else []

    def rowCount(  # noqa: N802 - Qt API override
        self,
        parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex = _INVALID_INDEX,
    ) -> int:
        return len(self._items)

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
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            col = index.column()
            if col == 0:
                return hex(int(item.offset))
            if col == 1:
                return str(item.name)
            if col == 2:
                return str(item.tinfo) if item.tinfo else ""
            if col == 3:
                return int(item.size)
            if col == 4:
                return bool(item.enabled)
        return None

    def add_row(self, member: AbstractMember) -> None:
        """Insert member maintaining sorted order by offset."""
        import bisect

        self.beginResetModel()  # noqa: N802 - Qt API
        # bisect.insort requires __lt__
        keys = [m.offset for m in self._items]
        idx = bisect.bisect_left(keys, int(member.offset))
        self._items.insert(idx, member)
        self.endResetModel()  # noqa: N802 - Qt API

    def clear(self) -> None:
        self.beginResetModel()  # noqa: N802 - Qt API
        self._items = []
        self.endResetModel()  # noqa: N802 - Qt API

    @property
    def items(self) -> list[Any]:
        return list(self._items)
