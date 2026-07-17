"""Structure Builder widget — dock form for the temp struct model.

Ported from ``refs/HexRaysPyTools/HexRaysPyTools/forms.py:StructureBuilder``.

This widget is the main UI for the struct reconstruction feature. It
hosts a ``QTableView`` bound to a :class:`StructureModel` plus a row of
buttons that invoke the model's operations (finalize, disable, enable,
origin, array, pack, unpack, remove, resolve, load, clear,
recognize-shape, view-templates, view-structure).

Behaviour that requires live Hex-Rays ctree / chooser dialogs is
exercised end-to-end via ``idat`` headless + manual right-click testing;
unit tests cover widget construction and signal wiring (see
``tests/ui/widgets/test_structure_builder.py``).
"""

from __future__ import annotations

import logging
from typing import Any

import idaapi  # type: ignore[import-not-found]
import idc  # type: ignore[import-not-found]
from PySide6 import QtCore, QtGui, QtWidgets

from ..widgets_common import form_to_pyside_widget

logger = logging.getLogger(__name__)


class StructureBuilder(idaapi.PluginForm):  # type: ignore[misc]
    """Dock form wrapping a Qt table view + button row for the structure builder.

    Mirrors the original ``forms.StructureBuilder`` — 14 buttons across
    two stacked views (the structure table and the templated-types
    form). End-to-end correctness requires Hex-Rays APIs that the
    ``tools/mock_ida.py`` mock does not reproduce.
    """

    def __init__(self, structure_model: Any) -> None:
        super().__init__()
        self.structure_model = structure_model
        self.parent: QtWidgets.QWidget | None = None  # noqa: N806 - Qt naming
        self._stl_list: QtWidgets.QListWidget | None = None
        self._stl_title_fields: QtWidgets.QLabel | None = None
        self._stl_title_struct: QtWidgets.QLabel | None = None
        self._stl_struct_view: QtWidgets.QTextEdit | None = None
        self._stl_widget: QtWidgets.QWidget | None = None
        self._stl_form_layout: QtWidgets.QFormLayout | None = None
        self._stack: QtWidgets.QStackedWidget | None = None
        self._struct_view: QtWidgets.QTableView | None = None

    def OnCreate(self, form: Any) -> None:  # noqa: N802, N806
        self.parent = form_to_pyside_widget(form)
        self._init_ui()

    def _init_ui(self) -> None:
        assert self.parent is not None  # set in OnCreate
        self.parent.setStyleSheet(
            "QTableView {background-color: transparent; selection-background-color: #87bdd8;}"
            "QHeaderView::section {background-color: transparent; border: 0.5px solid;}"
            "QPushButton {width: 50px; height: 20px;}"
        )
        self.parent.resize(400, 600)
        self.parent.setWindowTitle("Structure Builder")

        btn_finalize = QtWidgets.QPushButton("&Finalize")
        btn_disable = QtWidgets.QPushButton("&Disable")
        btn_enable = QtWidgets.QPushButton("&Enable")
        btn_origin = QtWidgets.QPushButton("&Origin")
        btn_array = QtWidgets.QPushButton("&Array")
        btn_pack = QtWidgets.QPushButton("&Pack")
        btn_unpack = QtWidgets.QPushButton("&Unpack")
        btn_remove = QtWidgets.QPushButton("&Remove")
        btn_resolve = QtWidgets.QPushButton("Resolve")
        btn_load = QtWidgets.QPushButton("&Load")
        btn_clear = QtWidgets.QPushButton("Clear")
        btn_recognize = QtWidgets.QPushButton("Recognize Shape")
        btn_recognize.setStyleSheet("QPushButton {width: 100px; height: 20px;}")
        btn_stl = QtWidgets.QPushButton("Templated Types View")
        btn_stl.setStyleSheet("QPushButton {width: 150px; height: 20px;}")
        btn_struct = QtWidgets.QPushButton("Structure View")
        btn_struct.setStyleSheet("QPushButton {width: 150px; height: 20px;}")
        btn_reload_stl_list = QtWidgets.QPushButton("Reload Templated Types TOML")
        btn_reload_stl_list.setFixedWidth(300)
        btn_open_stl_toml = QtWidgets.QPushButton("Open Templated Types TOML")
        btn_open_stl_toml.setFixedWidth(300)

        # Single-character shortcuts (the original wires these explicitly).
        for btn, key in (
            (btn_finalize, "f"),
            (btn_disable, "d"),
            (btn_enable, "e"),
            (btn_origin, "o"),
            (btn_array, "a"),
            (btn_pack, "p"),
            (btn_unpack, "u"),
            (btn_remove, "r"),
            (btn_load, "l"),
        ):
            btn.setShortcut(key)

        # ---- Structure table view -------------------------------------
        self._struct_view = QtWidgets.QTableView()
        self._struct_view.setModel(self.structure_model)
        self._struct_view.verticalHeader().setVisible(False)
        self._struct_view.verticalHeader().setDefaultSectionSize(24)
        self._struct_view.horizontalHeader().setStretchLastSection(True)
        self._struct_view.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )

        # ---- Templated Types side panel -------------------------------
        self._stl_list = QtWidgets.QListWidget()
        tmpl = getattr(self.structure_model, "tmpl_types", None)
        if tmpl is not None:
            for item in tmpl.keys:
                self._stl_list.addItem(item)
        self._stl_list.setFixedWidth(300)
        if self._stl_list.count() > 0:
            self._stl_list.setCurrentRow(0)

        self._stl_title_fields = QtWidgets.QLabel("Selected Type: ")
        self._stl_title_struct = QtWidgets.QLabel("Creating Type: ")
        self._stl_struct_view = QtWidgets.QTextEdit()
        self._stl_struct_view.setReadOnly(True)
        font = QtGui.QFont("Courier", 11)
        self._stl_struct_view.setFont(font)

        self._stl_widget = QtWidgets.QWidget()
        self._stl_form_layout = QtWidgets.QFormLayout()
        self._update_stl_form()

        stl_layout = QtWidgets.QGridLayout()
        stl_layout.addWidget(QtWidgets.QLabel("Type List"), 0, 0)
        stl_layout.addWidget(self._stl_title_fields, 0, 1)
        stl_layout.addWidget(self._stl_title_struct, 0, 2)
        stl_layout.addWidget(self._stl_struct_view, 1, 2)
        stl_layout.addWidget(self._stl_list, 1, 0)
        stl_layout.addWidget(self._stl_widget, 1, 1)
        stl_layout.addWidget(btn_reload_stl_list, 2, 0)
        stl_layout.addWidget(btn_open_stl_toml, 3, 0)
        stl_layout.setColumnStretch(1, 1)
        stl_layout.setColumnStretch(2, 1)
        stl_view = QtWidgets.QWidget()
        stl_view.setLayout(stl_layout)

        # ---- Button grid ----------------------------------------------
        grid_box = QtWidgets.QGridLayout()
        grid_box.setSpacing(0)
        grid_box.addWidget(btn_finalize, 0, 0)
        grid_box.addWidget(btn_enable, 0, 1)
        grid_box.addWidget(btn_disable, 0, 2)
        grid_box.addWidget(btn_origin, 0, 3)
        grid_box.addItem(
            QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Policy.Expanding), 0, 6
        )
        grid_box.addWidget(btn_array, 1, 0)
        grid_box.addWidget(btn_pack, 1, 1)
        grid_box.addWidget(btn_unpack, 1, 2)
        grid_box.addWidget(btn_remove, 1, 3)
        grid_box.addWidget(btn_resolve, 0, 4)
        grid_box.addWidget(btn_load, 1, 4)
        grid_box.addWidget(btn_stl, 0, 5)
        grid_box.addWidget(btn_struct, 1, 5)
        grid_box.addItem(
            QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Policy.Expanding), 1, 6
        )
        grid_box.addWidget(btn_recognize, 0, 7)
        grid_box.addWidget(btn_clear, 1, 7)

        # ---- Stacked views --------------------------------------------
        self._stack = QtWidgets.QStackedWidget()
        self._stack.addWidget(self._struct_view)
        self._stack.addWidget(stl_view)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self._stack)
        vbox.addLayout(grid_box)
        self.parent.setLayout(vbox)

        # ---- Signal wiring --------------------------------------------
        def selected_indexes() -> list[QtCore.QModelIndex]:
            assert self._struct_view is not None
            return list(self._struct_view.selectedIndexes())

        btn_finalize.clicked.connect(self.structure_model.finalize)
        btn_disable.clicked.connect(lambda: self.structure_model.disable_rows(selected_indexes()))
        btn_enable.clicked.connect(lambda: self.structure_model.enable_rows(selected_indexes()))
        btn_origin.clicked.connect(lambda: self.structure_model.set_origin(selected_indexes()))
        btn_array.clicked.connect(lambda: self.structure_model.make_array(selected_indexes()))
        btn_pack.clicked.connect(lambda: self.structure_model.pack_substructure(selected_indexes()))
        btn_unpack.clicked.connect(
            lambda: self.structure_model.unpack_substructure(selected_indexes())
        )
        btn_remove.clicked.connect(lambda: self.structure_model.remove_items(selected_indexes()))
        btn_resolve.clicked.connect(self.structure_model.resolve_types)
        btn_stl.clicked.connect(lambda: self._stack.setCurrentIndex(1) if self._stack else None)
        btn_struct.clicked.connect(lambda: self._stack.setCurrentIndex(0) if self._stack else None)
        btn_load.clicked.connect(self.structure_model.load_struct)
        btn_clear.clicked.connect(self.structure_model.clear)
        btn_recognize.clicked.connect(
            lambda: self.structure_model.recognize_shape(selected_indexes())
        )

        if self._struct_view is not None:
            self._struct_view.activated.connect(self.structure_model.activated)
            self.structure_model.dataChanged.connect(self._struct_view.clearSelection)
        if self._stl_list is not None:
            self._stl_list.currentRowChanged.connect(self._update_stl_form)
        btn_reload_stl_list.clicked.connect(self._reload_stl_list)
        btn_open_stl_toml.clicked.connect(self._open_dialog_stl_file)

    # ------------------------------------------------------------------
    # Templated Types form helpers — mirror the original ``forms.StructureBuilder``
    # ------------------------------------------------------------------
    def _update_stl_form(self) -> None:
        if self._stl_list is None or self._stl_form_layout is None or self._stl_widget is None:
            return
        try:
            current = self._stl_list.currentItem()
            if current is None:
                return
            key = current.text()
            tmpl = getattr(self.structure_model, "tmpl_types", None)
            if tmpl is None:
                return
            if self._stl_title_fields is not None:
                self._stl_title_fields.setText(f"Selected Type: {key}")
            types = tmpl.get_types(key) or []
            # Remove old widgets from form layout.
            for i in reversed(range(self._stl_form_layout.count())):
                item = self._stl_form_layout.itemAt(i)
                if item is None:
                    continue
                w = item.widget()
                if w is not None:
                    w.setParent(None)
            for t in types:
                e1 = QtWidgets.QLineEdit()
                e2 = QtWidgets.QLineEdit()
                self._stl_form_layout.addRow(QtWidgets.QLabel(f"{t} Type"), e1)
                self._stl_form_layout.addRow(QtWidgets.QLabel(f"{t} Name"), e2)
                e1.textChanged.connect(lambda: self._reload_stl_struct(key))
                e2.textChanged.connect(lambda: self._reload_stl_struct(key))
            btn_set_type = QtWidgets.QPushButton("Set Type")
            self._stl_form_layout.addRow(btn_set_type)
            self._stl_widget.setLayout(self._stl_form_layout)
            self._reload_stl_struct(key)
            btn_set_type.clicked.connect(lambda: self._call_set_stl_type(key))
        except Exception as e:  # noqa: BLE001 — defensive, mirrors original
            logger.debug("update_stl_form failed: %s", e)

    def _reload_stl_list(self) -> None:
        if self._stl_list is None:
            return
        tmpl = getattr(self.structure_model, "tmpl_types", None)
        if tmpl is None:
            return
        self._stl_list.clear()
        tmpl.reload_types()
        for item in tmpl.keys:
            self._stl_list.addItem(item)

    def _reload_stl_struct(self, key: str) -> None:
        if self._stl_struct_view is None or self._stl_title_struct is None:
            return
        try:
            tmpl = getattr(self.structure_model, "tmpl_types", None)
            if tmpl is None:
                return
            struct = tmpl.get_struct(key)
            base_name = tmpl.get_base_name(key) or ""
            args = self._get_stl_args(key)
            if struct:
                self._stl_struct_view.setPlainText(struct.format(*args))
            self._stl_title_struct.setText(f"Creating Type: {base_name.format(*args)}")
        except Exception as e:  # noqa: BLE001 — defensive, mirrors original
            logger.debug("reload_stl_struct failed: %s", e)

    def _get_stl_args(self, key: str) -> tuple[str, ...]:
        if self._stl_widget is None:
            return ()
        args: tuple[str, ...] = ()
        for w in self._stl_widget.findChildren(QtWidgets.QLineEdit):
            text = w.text() or "$void$"
            args = args + (text,)
        return args

    def _call_set_stl_type(self, key: str) -> None:
        args = self._get_stl_args(key)
        for i, arg in enumerate(args):
            if i % 2 == 0:
                # Type name validation.
                import re as _re

                if not _re.match(r"^[a-zA-Z_]([\w_](::){0,2})+(?<!:)\**$", arg):
                    logger.warning("Type name %r is an invalid type name", arg)
                    return
            else:
                import re as _re

                if not _re.match(r"^\w+$", arg):
                    logger.warning("Type name %r is an invalid name", arg)
                    return
        self.structure_model.set_stl_type(key, args)

    def _open_dialog_stl_file(self) -> None:
        import os

        tmpl = getattr(self.structure_model, "tmpl_types", None)
        if tmpl is None:
            return
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Open TOML file",
            os.path.join(idc.idadir(), "plugins", "HexRaysPyTools-ng", "types"),
            "Toml file (*.toml)",
        )
        logger.info("Opening %s", file_name)
        tmpl.set_file_path(file_name)
        self._reload_stl_list()

    def OnClose(self, form: Any) -> None:  # noqa: N802, N806
        # Mirrors original — intentionally empty (no state to flush).
        pass

    def Show(self, caption: str | None = None, options: int = 0) -> Any:  # noqa: N802 - IDA PluginForm API
        return idaapi.PluginForm.Show(self, caption, options=options)
