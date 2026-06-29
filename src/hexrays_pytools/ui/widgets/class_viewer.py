"""Class Viewer widget — the dock form for the class browser."""
from __future__ import annotations

from typing import Any

import idaapi  # type: ignore[import-not-found]
from PySide6 import QtWidgets

from ..widgets_common import form_to_pyside_widget


class ClassViewer(idaapi.PluginForm):  # type: ignore[misc]
    """Dock form for the class browser tree view."""

    def __init__(self, proxy_model: Any, class_model: Any) -> None:
        super().__init__()
        self.proxy_model = proxy_model
        self.class_model = class_model
        self.parent: QtWidgets.QWidget | None = None  # noqa: N806

    def OnCreate(self, form: Any) -> None:  # noqa: N802, N806
        self.parent = form_to_pyside_widget(form)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        # Filter line edit
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self.filter_edit)
        # Tree view
        self.class_tree = QtWidgets.QTreeView()
        self.class_tree.setModel(self.proxy_model)
        layout.addWidget(self.class_tree)
        assert self.parent is not None  # set in OnCreate before _init_ui
        self.parent.setLayout(layout)
        self.proxy_model.setSourceModel(self.class_model)

    def _on_filter_changed(self, text: str) -> None:
        if hasattr(self.proxy_model, "set_regexp_filter"):
            self.proxy_model.set_regexp_filter(text)

