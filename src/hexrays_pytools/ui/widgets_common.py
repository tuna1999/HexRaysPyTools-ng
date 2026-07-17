"""Shared helpers for IDA ``PluginForm`` widgets.

These helpers isolate IDA-version-specific quirks of wrapping an IDA form
handle (``TWidget*``) into a PySide6 ``QWidget`` so the individual widget
modules stay small and version-agnostic.
"""

from __future__ import annotations

from typing import Any, cast

import idaapi  # type: ignore[import-not-found]
from PySide6 import QtWidgets


def form_to_pyside_widget(form: Any) -> QtWidgets.QWidget:
    """Wrap an IDA form handle into a PySide6 ``QWidget``.

    Why this exists:
        IDA 9.4's ``idaapi.PluginForm.FormToPySideWidget`` is broken. It
        ultimately calls ``ctx.QtGui.QWidget.FromCapsule(tw)``, but neither
        ``QWidget`` nor ``FromCapsule`` exists in ``PySide6.QtGui`` — they
        live in ``PySide6.QtWidgets``. The lookup therefore always raises
        ``AttributeError: module 'PySide6.QtGui' has no attribute 'QWidget'``
        at ``OnCreate`` time, regardless of what is injected into the
        ``__main__`` namespace.

    What we do instead:
        ``PluginForm.TWidgetToQtPythonWidget`` (the ``FormToPyQtWidget``
        alias) is the sibling static method that actually works: it wraps
        the raw pointer via ``shiboken6.Shiboken.wrapInstance`` with
        ``PySide6.QtWidgets.QWidget`` and walks ``metaObject()`` to recover
        the concrete subclass. Despite its PyQt-leaning name, the
        implementation is pure PySide6 — it is the correct, stable path.

    :param form: The ``TWidget*`` handle passed to ``PluginForm.OnCreate``.
    :returns: The wrapped ``QWidget`` to populate with child widgets.
    """
    # ``cast`` documents the IDA runtime contract: TWidgetToQtPythonWidget
    # always returns a QWidget in real IDA. Mypy can't see that because
    # mock_ida types the staticmethod as ``-> Any``.
    return cast(QtWidgets.QWidget, idaapi.PluginForm.TWidgetToQtPythonWidget(form))
