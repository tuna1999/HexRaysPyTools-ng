"""Structure Builder widget — the dock form for the temp struct model."""
from __future__ import annotations

from typing import Any

import idaapi  # type: ignore[import-not-found]
from PySide6 import QtWidgets

from ..widgets_common import form_to_pyside_widget


class StructureBuilder(idaapi.PluginForm):  # type: ignore[misc]
    """Dock form wrapping a Qt table view for the structure builder."""

    def __init__(self, structure_model: Any) -> None:
        super().__init__()
        self.structure_model = structure_model
        self.parent: QtWidgets.QWidget | None = None  # noqa: N806 - Qt naming

    def OnCreate(self, form: Any) -> None:  # noqa: N802, N806
        self.parent = form_to_pyside_widget(form)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        self.struct_view = QtWidgets.QTableView()
        self.struct_view.setModel(self.structure_model)
        layout.addWidget(self.struct_view)
        # Finalize button
        btn_finalize = QtWidgets.QPushButton("Finalize")
        btn_finalize.clicked.connect(self._on_finalize)
        layout.addWidget(btn_finalize)
        assert self.parent is not None  # set in OnCreate before _init_ui
        self.parent.setLayout(layout)

    def _on_finalize(self) -> None:
        if hasattr(self.structure_model, "finalize"):
            self.structure_model.finalize()

