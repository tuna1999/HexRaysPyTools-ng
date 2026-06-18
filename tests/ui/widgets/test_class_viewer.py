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
