# Task 2.10 Brief: domain/recon/structure_model.py

## Files (2)
1. `src/hexrays_pytools/domain/recon/structure_model.py`
2. `tests/domain/recon/test_structure_model.py`

## `structure_model.py` (verbatim — Qt model for the builder)

```python
"""QAbstractTableModel for the Structure Builder widget.

Replaces the Qt model portion of `core/temporary_structure.py:TemporaryStructureModel`.
Uses PySide6. For testing, mocks are provided via `tools/mock_ida.py`.
"""
from __future__ import annotations
import logging
from typing import Any

import idaapi  # type: ignore[import-not-found]
from PySide6 import QtCore  # type: ignore[import-not-found]

from .member import AbstractMember

logger = logging.getLogger(__name__)


class StructureModel(QtCore.QAbstractTableModel):
    """Qt table model for the structure builder.

    Columns: Offset, Name, Type, Size, Enabled.
    """

    HEADERS = ["Offset", "Name", "Type", "Size", "Enabled"]

    def __init__(self, items: list | None = None) -> None:
        super().__init__()
        self._items: list = items if items is not None else []

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._items)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.DisplayRole) -> Any:
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        if role == QtCore.Qt.DisplayRole:
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
        self.beginResetModel()
        # bisect.insort requires __lt__
        keys = [m.offset for m in self._items]
        idx = bisect.bisect_left(keys, int(member.offset))
        self._items.insert(idx, member)
        self.endResetModel()

    def clear(self) -> None:
        self.beginResetModel()
        self._items = []
        self.endResetModel()

    @property
    def items(self) -> list:
        return list(self._items)
```

## `test_structure_model.py` (verbatim)

```python
"""Test StructureModel with Qt offscreen platform."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from hexrays_pytools.domain.recon.structure_model import StructureModel
from hexrays_pytools.domain.recon.member import AbstractMember


def test_model_init_empty() -> None:
    m = StructureModel()
    assert m.rowCount() == 0
    assert m.columnCount() == 5


def test_model_header_data() -> None:
    m = StructureModel()
    from PySide6 import QtCore
    assert m.headerData(0, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole) == "Offset"
    assert m.headerData(1, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole) == "Name"
    assert m.headerData(2, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole) == "Type"


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
```

Add `from unittest.mock import MagicMock` to imports.

## Verification
```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=src pytest tests/domain/recon/test_structure_model.py -v
python -m mypy --strict src/hexrays_pytools/domain/recon/structure_model.py
python -m ruff check src/hexrays_pytools/domain/recon/structure_model.py tests/domain/recon/test_structure_model.py
```

## Commit
```bash
git add src/hexrays_pytools/domain/recon/structure_model.py tests/domain/recon/test_structure_model.py
git commit -m "feat(recon): add StructureModel (Qt QAbstractTableModel for builder)"
```

## Report
`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.10-report.md`