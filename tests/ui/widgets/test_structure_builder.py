"""Smoke test: StructureBuilder instantiates and accepts a model."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock


def test_structure_builder_init() -> None:
    """StructureBuilder accepts a model and exposes it."""
    from hexrays_pytools.ui.widgets.structure_builder import StructureBuilder
    model = MagicMock()
    sb = StructureBuilder(model)
    assert sb.structure_model is model


"""F5: extended widget coverage for structure_builder."""


def test_structure_builder_init_no_raise_with_model() -> None:
    """StructureBuilder() with valid model doesn't raise in __init__."""
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")

    from hexrays_pytools.domain.recon.workspace import ReconWorkspace
    from hexrays_pytools.ui.widgets.structure_builder import StructureBuilder

    builder = StructureBuilder(ReconWorkspace())
    assert builder is not None


def test_structure_builder_init_with_none_model() -> None:
    """StructureBuilder(None) is tolerated (widget handles gracefully)."""
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")

    from hexrays_pytools.ui.widgets.structure_builder import StructureBuilder

    builder = StructureBuilder(None)
    assert builder is not None


def test_structure_builder_column_count() -> None:
    """StructureBuilder exposes columnCount via its table view + model binding."""
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")

    import sys

    from PySide6 import QtWidgets

    from hexrays_pytools.domain.recon.structure_model import StructureModel
    from hexrays_pytools.ui.widgets import structure_builder
    from hexrays_pytools.ui.widgets.structure_builder import StructureBuilder

    # Ensure a QApplication exists before constructing any QWidget subclass.
    QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    model = StructureModel()
    builder = StructureBuilder(model)
    # Stub form_to_pyside_widget on the *widget's module* (it was imported by
    # name into the widget's namespace, so widgets_common reassignment is a no-op).
    original = structure_builder.form_to_pyside_widget
    structure_builder.form_to_pyside_widget = lambda _form: QtWidgets.QWidget()
    try:
        builder.OnCreate(None)
        # table view is wired to the structure model; columnCount comes from it.
        assert builder._struct_view.model() is builder.structure_model
        # 4 columns: Offset, Type, Name, Comment (mirrors original
        # TemporaryStructureModel).
        assert builder._struct_view.model().columnCount() == 4
    finally:
        structure_builder.form_to_pyside_widget = original
