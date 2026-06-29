"""Tests for ``ui.widgets_common.form_to_pyside_widget``.

These guard the IDA 9.4 ``PluginForm.FormToPySideWidget`` regression:
that function calls ``ctx.QtGui.QWidget.FromCapsule(tw)``, but neither
``QWidget`` nor ``FromCapsule`` exists in ``PySide6.QtGui``, so it always
raises ``AttributeError`` at ``OnCreate`` time. The helper must route
through the working ``TWidgetToQtPythonWidget`` wrapper and must NEVER
touch the broken alias.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from typing import Any
from unittest.mock import MagicMock

import idaapi  # type: ignore[import-not-found]  # mocked by conftest

from hexrays_pytools.ui.widgets_common import form_to_pyside_widget

_FORM = "FORM_HANDLE_SENTINEL"


def test_uses_working_twidget_to_qtpython_wrapper(monkeypatch: Any) -> None:
    """form_to_pyside_widget delegates to TWidgetToQtPythonWidget and forwards the form handle."""
    fake_widget = MagicMock(name="wrapped_qwidget")
    calls: list[Any] = []

    def fake_wrap(form: Any) -> Any:
        calls.append(form)
        return fake_widget

    monkeypatch.setattr(
        idaapi.PluginForm, "TWidgetToQtPythonWidget", staticmethod(fake_wrap)
    )
    # Belt-and-suspenders: ensure the broken alias is never reached even by accident.
    monkeypatch.setattr(
        idaapi.PluginForm,
        "FormToPySideWidget",
        staticmethod(lambda form: (_ for _ in ()).throw(AssertionError("must not use broken alias"))),
    )

    result = form_to_pyside_widget(_FORM)

    assert result is fake_widget
    assert calls == [_FORM]


def test_never_routes_through_broken_formtopyside_alias(monkeypatch: Any) -> None:
    """Even if IDA's FormToPySideWidget raises the 9.4 AttributeError, the helper must not call it.

    This is the regression guard for the crash originally reported:
    ``AttributeError: module 'PySide6.QtGui' has no attribute 'QWidget'``.
    Reverting the helper (or either widget) to ``idaapi.PluginForm.FormToPySideWidget``
    makes this test fail.
    """

    def broken_alias(form: Any) -> Any:
        raise AttributeError("module 'PySide6.QtGui' has no attribute 'QWidget'")

    monkeypatch.setattr(
        idaapi.PluginForm, "FormToPySideWidget", staticmethod(broken_alias)
    )
    monkeypatch.setattr(
        idaapi.PluginForm, "TWidgetToQtPythonWidget", staticmethod(lambda f: MagicMock())
    )

    # Must not raise — proving the broken code path is avoided.
    assert form_to_pyside_widget(_FORM) is not None
