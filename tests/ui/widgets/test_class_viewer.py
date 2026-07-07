"""Smoke test: ClassViewer accepts proxy + class models."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock


def test_class_viewer_init() -> None:
    from hexrays_pytools.ui.widgets.class_viewer import ClassViewer
    proxy = MagicMock()
    cls_model = MagicMock()
    cv = ClassViewer(proxy, cls_model)
    assert cv.proxy_model is proxy
    assert cv.class_model is cls_model


"""F5: extended widget coverage for class_viewer."""


def test_class_viewer_init_no_raise_with_model() -> None:
    """ClassViewer() with valid model doesn't raise in __init__."""
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")

    from hexrays_pytools.domain.browser.proxy_model import ProxyModel
    from hexrays_pytools.domain.browser.tree_model import TreeModel
    from hexrays_pytools.ui.widgets.class_viewer import ClassViewer

    viewer = ClassViewer(ProxyModel(), TreeModel())
    assert viewer is not None


def test_class_viewer_column_count() -> None:
    """ClassViewer exposes columnCount via its tree view + proxy model binding."""
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")

    import sys

    from PySide6 import QtWidgets

    from hexrays_pytools.domain.browser.proxy_model import ProxyModel
    from hexrays_pytools.domain.browser.tree_model import TreeModel
    from hexrays_pytools.ui.widgets import class_viewer
    from hexrays_pytools.ui.widgets.class_viewer import ClassViewer

    # Ensure a QApplication exists before constructing any QWidget subclass.
    QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    proxy = ProxyModel()
    viewer = ClassViewer(proxy, TreeModel())
    # Stub form_to_pyside_widget on the *widget's module* (it was imported by
    # name into the widget's namespace, so widgets_common reassignment is a no-op).
    original = class_viewer.form_to_pyside_widget
    class_viewer.form_to_pyside_widget = lambda _form: QtWidgets.QWidget()
    try:
        viewer.OnCreate(None)
        # columnCount comes from the proxy model bound to the QTreeView.
        assert viewer.class_tree.model() is proxy
        assert viewer.class_tree.model().columnCount() >= 0
    finally:
        class_viewer.form_to_pyside_widget = original
