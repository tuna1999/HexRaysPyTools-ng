"""Test Action base classes."""
from unittest.mock import MagicMock

import pytest

from hexrays_pytools.domain.actions.action import (
    Action,
    HexRaysPopupAction,
    HexRaysPopupRequestHandler,
    HexRaysXrefAction,
)


def test_action_name_uses_class_name() -> None:
    a = Action()
    assert a.name == "HexRaysPyTools:Action"


def test_action_init_accepts_session() -> None:
    session = MagicMock()
    a = Action(session=session)
    assert a._session is session


def test_action_activate_raises_not_implemented() -> None:
    a = Action()
    with pytest.raises(NotImplementedError):
        a.activate(None)


def test_hexrays_popup_action_check_raises() -> None:
    a = HexRaysPopupAction()
    with pytest.raises(NotImplementedError):
        a.check(None)


def test_hexrays_xref_action_check_raises() -> None:
    a = HexRaysXrefAction()
    with pytest.raises(NotImplementedError):
        a.check(None)


def test_hexrays_xref_action_attaches_in_local_types_popup() -> None:
    """Local Types has no hxe_populating_popup, so update attaches directly."""
    idaapi = __import__("idaapi")

    class _X(HexRaysXrefAction):
        def activate(self, ctx):  # type: ignore[no-untyped-def]
            pass

        def check(self, hx_view):  # type: ignore[no-untyped-def]
            return True

    action = _X()
    ctx = MagicMock()
    ctx.widget_type = idaapi.BWN_LOCTYPS
    idaapi.attach_action_to_popup.reset_mock()

    assert action.update(ctx) == int(idaapi.AST_ENABLE_FOR_WIDGET)
    idaapi.attach_action_to_popup.assert_called_once_with(
        ctx.widget, None, action.name, action.menu_path
    )


def test_hexrays_xref_action_accepts_legacy_tilist_widget() -> None:
    idaapi = __import__("idaapi")

    assert HexRaysXrefAction._is_local_types_widget(idaapi.BWN_LOCTYPS) is True
    assert HexRaysXrefAction._is_local_types_widget(idaapi.BWN_TILVIEW) is True
    assert HexRaysXrefAction._is_local_types_widget(idaapi.BWN_TILIST) is True


def test_popup_request_handler_calls_attach_when_check_passes() -> None:
    """Request handler attaches action to popup when check returns True.

    The attach uses the action's ``menu_path`` (4th arg) so the action lands
    in its submenu group, not at the popup root.
    """
    idaapi = __import__("idaapi")
    action = MagicMock()
    action.check.return_value = True
    action.name = "test_action"
    action.menu_path = "HexRaysPyTools-ng/"
    handler = HexRaysPopupRequestHandler(action)
    form = MagicMock()
    popup = MagicMock()
    hx_view = MagicMock()
    handler.handle(0, form, popup, hx_view)
    idaapi.attach_action_to_popup.assert_called_once_with(
        form, popup, "test_action", "HexRaysPyTools-ng/"
    )


def test_popup_request_handler_skips_when_check_fails() -> None:
    idaapi = __import__("idaapi")
    action = MagicMock()
    action.check.return_value = False
    handler = HexRaysPopupRequestHandler(action)
    handler.handle(0, MagicMock(), MagicMock(), MagicMock())
    idaapi.attach_action_to_popup.assert_not_called()


def test_popup_action_default_menu_path_is_group_root() -> None:
    """HexRaysPopupAction defaults to the HexRaysPyTools/ submenu root."""

    class _P(HexRaysPopupAction):
        description = "P"

        def activate(self, ctx):  # type: ignore[no-untyped-def]
            pass

        def check(self, hx_view):  # type: ignore[no-untyped-def]
            return True

    assert _P().menu_path == "HexRaysPyTools-ng/"


def test_plain_action_has_no_menu_path() -> None:
    """Non-popup Actions default to menu_path None (not in right-click menu)."""

    class _A(Action):
        description = "A"

        def activate(self, ctx):  # type: ignore[no-untyped-def]
            pass

    assert _A.menu_path is None
