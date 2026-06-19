# Task 3.4 Brief: domain/browser/proxy_model.py

## Files (2)
1. `src/hexrays_pytools/domain/browser/proxy_model.py`
2. `tests/domain/browser/test_proxy_model.py`

## `proxy_model.py` (verbatim — fixes B3: setFilterRegExp → setFilterRegularExpression)

```python
"""ProxyModel for filtering the class browser by name or function.

Replaces `core/classes.py:ProxyModel`. Uses `setFilterRegularExpression`
(was `setFilterRegExp`, removed in Qt6).
"""
from __future__ import annotations
import re

from PySide6 import QtCore  # type: ignore[import-not-found]


class ProxyModel(QtCore.QSortFilterProxyModel):
    """Filter Class nodes by name (or by function name with '!' prefix)."""

    def __init__(self) -> None:
        super().__init__()
        self.filter_by_function = False
        self._compile_error: str = ""

    def set_regexp_filter(self, regexp: str) -> None:
        """Set the filter. Prefix with '!' to filter by function names instead.

        Uses QRegularExpression (Qt6 API). Falls back to literal match on
        invalid patterns so bad regex doesn't crash the filter UI.
        """
        self.filter_by_function = bool(regexp) and regexp[0] == "!"
        pattern = regexp[1:] if self.filter_by_function else regexp
        try:
            compiled = QtCore.QRegularExpression(pattern)
            if not compiled.isValid():
                self._compile_error = compiled.errorString()
                self.setFilterRegularExpression(QtCore.QRegularExpression(""))  # no-op filter
                return
            self.setFilterRegularExpression(compiled)
        except Exception:  # noqa: BLE001 — defensive: any Qt error → no-op filter
            self.setFilterRegularExpression(QtCore.QRegularExpression(""))
        self._compile_error = ""

    def filterAcceptsRow(self, row: int, parent: QtCore.QModelIndex) -> bool:
        """Return True if the row matches the current filter.

        FIX B3: was `self.filterRegExp().indexIn(...)` (QRegExp);
        now uses `self.filterRegularExpression().match(...)` (QRegularExpression).
        """
        regex = self.filterRegularExpression()
        if not regex.pattern():
            return True
        index = self.sourceModel().index(row, 0, parent)
        if not index.isValid():
            return True
        item = index.internalPointer()
        node = getattr(item, "item", None)
        if self.filter_by_function and hasattr(node, "has_function"):
            return node.has_function(regex.pattern())
        # Default: match name (use stdlib re for portability)
        node_name = getattr(node, "name", "") or ""
        return bool(re.search(regex.pattern(), node_name))
```

## `test_proxy_model.py` (verbatim)

```python
"""Test ProxyModel with Qt offscreen."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from hexrays_pytools.domain.browser.proxy_model import ProxyModel


def test_proxy_model_init() -> None:
    m = ProxyModel()
    assert m.filter_by_function is False


def test_set_regexp_filter_class_name() -> None:
    m = ProxyModel()
    m.set_regexp_filter("Foo")
    assert m.filter_by_function is False


def test_set_regexp_filter_function_with_bang() -> None:
    """Prefix '!' switches to function-name filter mode."""
    m = ProxyModel()
    m.set_regexp_filter("!doSomething")
    assert m.filter_by_function is True


def test_set_regexp_filter_empty() -> None:
    m = ProxyModel()
    m.set_regexp_filter("")
    assert m.filter_by_function is False


def test_set_regexp_filter_invalid_falls_back_to_noop() -> None:
    """Invalid regex pattern doesn't crash; filter becomes no-op."""
    m = ProxyModel()
    m.set_regexp_filter("[invalid")  # unmatched bracket
    # Filter should still work (just not filter anything out)
    assert m._compile_error != "" or m.filterRegularExpression().pattern() == ""


def test_filter_accepts_row_no_pattern() -> None:
    """With no pattern set, all rows are accepted."""
    m = ProxyModel()
    parent = MagicMock()
    assert m.filterAcceptsRow(0, parent) is True


def test_filter_accepts_row_matches_name() -> None:
    """A name matching the regex is accepted."""
    m = ProxyModel()
    m.set_regexp_filter("Foo")
    # Build a fake source index with internalPointer returning a node
    src = MagicMock()
    node = MagicMock()
    node.name = "FooBar"
    item = MagicMock()
    item.item = node
    idx = MagicMock()
    idx.isValid.return_value = True
    idx.internalPointer.return_value = item
    src.index.return_value = idx
    m.setSourceModel(src)
    assert m.filterAcceptsRow(0, MagicMock()) is True
```

Add `from unittest.mock import MagicMock` to imports.

## Verification
```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=src pytest tests/domain/browser/test_proxy_model.py -v
python -m mypy --strict src/hexrays_pytools/domain/browser/proxy_model.py
python -m ruff check src/hexrays_pytools/domain/browser/proxy_model.py tests/domain/browser/test_proxy_model.py
```

## Commit
```bash
git add src/hexrays_pytools/domain/browser/proxy_model.py tests/domain/browser/test_proxy_model.py
git commit -m "feat(browser): add ProxyModel (B3 fix: setFilterRegExp → setFilterRegularExpression)"
```

## Report
`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-3.4-report.md`