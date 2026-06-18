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
    m = HxCallbackManager()
    m.install()
    idaapi.install_hexrays_callback.assert_called_once()
    assert m._installed is True


def test_install_idempotent() -> None:
    """install() called twice doesn't re-install."""
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
