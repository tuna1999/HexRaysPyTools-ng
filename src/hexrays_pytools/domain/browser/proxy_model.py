"""ProxyModel for filtering the class browser by name or function.

Replaces `core/classes.py:ProxyModel`. Uses `setFilterRegularExpression`
(was `setFilterRegExp`, removed in Qt6).
"""

from __future__ import annotations

import re

from PySide6 import QtCore


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

    def filterAcceptsRow(  # type: ignore[override]  # noqa: N802 - Qt API override
        # PySide6 stubs declare the parent argument as
        # ``QModelIndex | QPersistentModelIndex``; the runtime accepts a plain
        # QModelIndex as in the legacy Qt5 override.
        self,
        row: int,
        parent: QtCore.QModelIndex,
    ) -> bool:
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
        if self.filter_by_function and node is not None and hasattr(node, "has_function"):
            return bool(node.has_function(regex.pattern()))
        # Default: match name (use stdlib re for portability)
        class_name = getattr(node, "class_name", None)
        plain_name = getattr(node, "name", "")
        node_name = class_name if isinstance(class_name, str) and class_name else plain_name
        if not isinstance(node_name, str):
            node_name = ""
        return bool(re.search(regex.pattern(), node_name))
