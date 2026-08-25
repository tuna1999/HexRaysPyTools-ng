"""Test HxCallbackManager."""
from unittest.mock import MagicMock

import idaapi  # type: ignore[import-not-found]

from hexrays_pytools.domain.actions.hx_callback import HxCallbackManager


def test_init_empty() -> None:
    m = HxCallbackManager()
    assert m._installed is False
    assert m._handlers == {}


def test_register_adds_handler() -> None:
    m = HxCallbackManager()
    handler = MagicMock()
    m.register(idaapi.hxe_maturity, handler)
    assert handler in m._handlers[idaapi.hxe_maturity]


def test_install_calls_idaapi() -> None:
    """install() calls install_hexrays_callback once."""
    idaapi.install_hexrays_callback.reset_mock()
    idaapi.install_hexrays_callback.return_value = True
    m = HxCallbackManager()
    assert m.install() is True
    idaapi.install_hexrays_callback.assert_called_once()
    assert m._installed is True


def test_install_failure_does_not_mark_installed() -> None:
    idaapi.install_hexrays_callback.reset_mock()
    idaapi.install_hexrays_callback.return_value = False
    m = HxCallbackManager()

    assert m.install() is False

    assert m._installed is False
    assert m.install() is False
    assert idaapi.install_hexrays_callback.call_count == 2


def test_install_idempotent() -> None:
    """install() called twice doesn't re-install."""
    idaapi.install_hexrays_callback.return_value = True
    m = HxCallbackManager()
    m.install()
    m.install()  # second call no-op
    assert idaapi.install_hexrays_callback.call_count == 1


def test_dispatch_invokes_handlers() -> None:
    m = HxCallbackManager()
    handler = MagicMock()
    m.register(idaapi.hxe_maturity, handler)
    m._dispatch(idaapi.hxe_maturity, "arg1")
    handler.handle.assert_called_once_with(idaapi.hxe_maturity, "arg1")


def test_dispatch_handles_exceptions() -> None:
    """Exceptions in one handler don't break other handlers."""
    m = HxCallbackManager()
    bad = MagicMock()
    bad.handle.side_effect = RuntimeError("boom")
    good = MagicMock()
    m.register(idaapi.hxe_maturity, bad)
    m.register(idaapi.hxe_maturity, good)
    m._dispatch(idaapi.hxe_maturity)
    good.handle.assert_called_once()


def test_detach_all_clears() -> None:
    m = HxCallbackManager()
    m.register(idaapi.hxe_maturity, MagicMock())
    m.detach_all()
    assert m._handlers == {}
    assert m._installed is False


def test_dispatch_records_handler_exception() -> None:
    """F4: handler exceptions are recorded in manager.errors."""
    m = HxCallbackManager()
    bad = MagicMock()
    bad.handle.side_effect = ValueError("boom")
    m.register(idaapi.hxe_maturity, bad)
    m._dispatch(idaapi.hxe_maturity)
    assert len(m.errors) == 1
    event_id, exc = m.errors[0]
    assert event_id == idaapi.hxe_maturity
    assert isinstance(exc, ValueError)
    assert str(exc) == "boom"


def test_session_recent_callback_errors_property() -> None:
    """F4: Session exposes recent_callback_errors property."""
    from hexrays_pytools.domain.session import Session

    s = Session()
    # No hx_callbacks wired yet — property returns empty list
    assert s.recent_callback_errors == []


def test_session_recent_callback_errors_caps_at_ten() -> None:
    """F4: Session.recent_callback_errors caps to most recent 10 errors."""
    from hexrays_pytools.domain.actions.hx_callback import HxCallbackManager
    from hexrays_pytools.domain.session import Session

    s = Session()
    m = HxCallbackManager()
    s.hx_callbacks = m

    bad = MagicMock()
    bad.handle.side_effect = RuntimeError("err")
    m.register(idaapi.hxe_maturity, bad)
    for _ in range(15):
        m._dispatch(idaapi.hxe_maturity)
    # manager.errors has 15 entries; property returns last 10
    assert len(m.errors) == 15
    assert len(s.recent_callback_errors) == 10
