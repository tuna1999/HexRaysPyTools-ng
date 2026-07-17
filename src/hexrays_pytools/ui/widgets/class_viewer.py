"""Class Viewer widget — the dock form for the class browser.

Ported from ``refs/HexRaysPyTools/HexRaysPyTools/forms.py:309-404``.

This widget is the main UI for the class reconstruction feature. It hosts
a ``QTreeView`` bound to a :class:`TreeModel`, a filter ``QLineEdit``,
and a context menu with 6 actions (collapse, expand, set_arg, rollback,
refresh, commit). End-to-end correctness requires Hex-Rays ctree / UDT
APIs that the ``tools/mock_ida.py`` mock does not reproduce — so the
widget is verified in real IDA via idat headless + manual interaction.
"""

from __future__ import annotations

import logging
from typing import Any

import idaapi  # type: ignore[import-not-found]
from PySide6 import QtCore, QtGui, QtWidgets

from ..widgets_common import form_to_pyside_widget

logger = logging.getLogger(__name__)


class ClassViewer(idaapi.PluginForm):  # type: ignore[misc]
    """Dock form for the class browser tree view.

    Mirrors the original ``ClassViewer`` line-by-line: 6 context-menu
    actions, ``class_tree.activated`` → ``open_function``, ``refreshed``
    signal → ``expandAll``, ``setFilterCaseSensitivity(Qt.CaseInsensitive)``,
    ``setSelectionMode(ExtendedSelection)``.
    """

    def __init__(self, proxy_model: Any, class_model: Any) -> None:
        super().__init__()
        self.proxy_model = proxy_model
        self.class_model = class_model
        self.parent: QtWidgets.QWidget | None = None  # noqa: N806
        # 6 context-menu actions are created in OnCreate (after the form
        # is parented) — creating them in __init__ with a None parent
        # segfaults under mock_ida's PySide6 shim.
        self.action_collapse: QtGui.QAction | None = None
        self.action_expand: QtGui.QAction | None = None
        self.action_set_arg: QtGui.QAction | None = None
        self.action_rollback: QtGui.QAction | None = None
        self.action_refresh: QtGui.QAction | None = None
        self.action_commit: QtGui.QAction | None = None
        self.menu: QtWidgets.QMenu | None = None
        self.class_tree: QtWidgets.QTreeView | None = None
        self.line_edit_filter: QtWidgets.QLineEdit | None = None

    def OnCreate(self, form: Any) -> None:  # noqa: N802, N806
        self.parent = form_to_pyside_widget(form)
        self._init_ui()

    def _init_ui(self) -> None:
        assert self.parent is not None
        layout = QtWidgets.QVBoxLayout()

        # Tree view — mirrors original (line 313).
        self.class_tree = QtWidgets.QTreeView()
        self.class_tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.class_tree.expandAll()
        self.class_tree.header().setStretchLastSection(True)
        self.class_tree.header().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.class_tree.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )

        # Filter line edit — mirrors original (line 314).
        self.line_edit_filter = QtWidgets.QLineEdit()

        # 6 context-menu actions — mirrors original (lines 316-321).
        # Parent them to the form root widget (avoids the mock_ida
        # segfault that triggers when QAction is constructed with None).
        action_parent = self.class_tree if self.class_tree is not None else self.parent
        self.action_collapse = QtGui.QAction("Collapse all", action_parent)
        self.action_expand = QtGui.QAction("Expand all", action_parent)
        self.action_set_arg = QtGui.QAction("Set First Argument Type", action_parent)
        self.action_rollback = QtGui.QAction("Rollback", action_parent)
        self.action_refresh = QtGui.QAction("Refresh", action_parent)
        self.action_commit = QtGui.QAction("Commit", action_parent)

        # Context menu — mirrors original (lines 370-375).
        self.menu = QtWidgets.QMenu(self.parent)
        self.menu.addAction(self.action_collapse)
        self.menu.addAction(self.action_expand)
        self.menu.addAction(self.action_refresh)
        self.menu.addAction(self.action_set_arg)
        self.menu.addAction(self.action_rollback)
        self.menu.addAction(self.action_commit)

        # Layout: tree at top, filter at bottom — mirrors original (lines 343-380).
        hbox = QtWidgets.QHBoxLayout()
        label_filter = QtWidgets.QLabel("&Filter:")
        label_filter.setBuddy(self.line_edit_filter)
        hbox.addWidget(label_filter)
        hbox.addWidget(self.line_edit_filter)
        layout.addWidget(self.class_tree)
        layout.addLayout(hbox)
        self.parent.setLayout(layout)

        # Model wiring — mirrors original (lines 349-352).
        self.proxy_model.setSourceModel(self.class_model)
        # FIX B3: explicit case-insensitive filter (matches original L350).
        try:
            self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        except AttributeError:
            # Older mock fallback.
            self.proxy_model.setFilterCaseSensitivity(0)
        self.class_tree.setModel(self.proxy_model)

        # Signal wiring — mirrors original (lines 358-386).
        self.action_collapse.triggered.connect(self.class_tree.collapseAll)
        self.action_expand.triggered.connect(self.class_tree.expandAll)
        self.action_set_arg.triggered.connect(
            lambda: self.class_model.set_first_argument_type(
                [self.proxy_model.mapToSource(idx) for idx in self.class_tree.selectedIndexes()]
            )
        )
        self.action_rollback.triggered.connect(lambda: self.class_model.rollback())
        self.action_refresh.triggered.connect(lambda: self.class_model.refresh())
        self.action_commit.triggered.connect(lambda: self.class_model.commit())

        # Refreshed signal — re-expand tree (mirrors original L368).
        try:
            self.class_model.refreshed.connect(self.class_tree.expandAll)
        except (AttributeError, RuntimeError, TypeError):
            logger.debug("TreeModel.refreshed signal not available")

        # Activated → open_function (mirrors original L382-384).
        try:
            self.class_tree.activated.connect(
                lambda idx: self.class_model.open_function(self.proxy_model.mapToSource(idx))
            )
        except (AttributeError, RuntimeError, TypeError):
            logger.debug("activated signal wiring skipped")

        # Custom context menu (mirrors original L385).
        try:
            self.class_tree.customContextMenuRequested.connect(self._show_menu)
        except (AttributeError, RuntimeError, TypeError):
            logger.debug("customContextMenuRequested wiring skipped")

        # Filter textChanged → proxy_model.set_regexp_filter (mirrors L386).
        self.line_edit_filter.textChanged.connect(self._on_filter_changed)

    def _on_filter_changed(self, text: str) -> None:
        if hasattr(self.proxy_model, "set_regexp_filter"):
            self.proxy_model.set_regexp_filter(text)

    def _show_menu(self, point: Any) -> None:
        """Right-click handler — mirrors original L395-404."""
        assert self.class_tree is not None
        # Enable set_arg only when ≥2 non-class rows are selected.
        if self.action_set_arg is not None:
            self.action_set_arg.setEnabled(True)
        if self.action_rollback is not None:
            self.action_rollback.setEnabled(False)  # noqa: ERA001
        indexes = list(self.class_tree.selectedIndexes())
        source_indexes = [self.proxy_model.mapToSource(idx) for idx in indexes if idx.column() == 0]
        if (
            len(source_indexes) > 1
            and any(
                len(getattr(idx.internalPointer().item, "children", [])) > 0
                for idx in source_indexes
            )
            and self.action_set_arg is not None
        ):
            self.action_set_arg.setEnabled(False)
        if self.menu is not None and self.class_tree is not None:
            self.menu.exec_(self.class_tree.mapToGlobal(point))
