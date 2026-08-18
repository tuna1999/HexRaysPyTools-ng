"""Unit tests for logging_setup.py — handler selection + idempotency.

These run under the pytest + mock_ida harness, so idaapi.msg is a
MagicMock → _ida_output_available() returns False → StreamHandler is
expected (not IdaOutputHandler).
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from hexrays_pytools.logging_setup import (
    _LOG_FORMAT,
    _ida_output_available,
    _make_handler,
    setup_logging,
)


def test_format_has_hexrays_prefix() -> None:
    """The log format string must start with [HexRaysPyTools]."""
    assert _LOG_FORMAT.startswith("[HexRaysPyTools]")


def test_format_has_levelname_and_module() -> None:
    """The format must include levelname and module for filtering."""
    assert "%(levelname)s" in _LOG_FORMAT
    assert "%(module)s" in _LOG_FORMAT


def test_ida_output_available_false_under_mock() -> None:
    """Under mock_ida, idaapi.msg is a MagicMock → returns False."""
    assert _ida_output_available() is False


def test_make_handler_returns_streamhandler_under_mock() -> None:
    """Under mock, _make_handler() must return a StreamHandler."""
    handler = _make_handler()
    assert isinstance(handler, logging.StreamHandler)


def test_setup_logging_idempotent_no_duplicate_handlers() -> None:
    """Calling setup_logging twice must not stack handlers."""
    root = logging.getLogger()
    setup_logging(logging.DEBUG)
    after_first = len(root.handlers)
    setup_logging(logging.DEBUG)
    after_second = len(root.handlers)
    assert after_first == after_second, "Handler count must not grow on re-call"
    # Exactly one HexRaysPyTools handler should be present.
    hx_handlers = [h for h in root.handlers if getattr(h, "_hexrays_pytools", False)]
    assert len(hx_handlers) == 1
    # Clean up: remove our handlers so other tests are not affected.
    for h in hx_handlers:
        root.removeHandler(h)


def test_setup_logging_sets_root_level() -> None:
    """setup_logging must set the root logger level."""
    root = logging.getLogger()
    try:
        setup_logging(logging.DEBUG)
        assert root.level == logging.DEBUG
        setup_logging(logging.WARNING)
        assert root.level == logging.WARNING
    finally:
        for h in list(root.handlers):
            if getattr(h, "_hexrays_pytools", False):
                root.removeHandler(h)
        root.setLevel(logging.WARNING)


def test_ida_output_handler_falls_to_stderr_on_failure() -> None:
    """If idaapi.msg raises, IdaOutputHandler.emit must write to stderr."""
    from hexrays_pytools.logging_setup import IdaOutputHandler

    handler = IdaOutputHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="test message",
        args=(),
        exc_info=None,
    )
    # Patch idaapi.msg (imported lazily inside emit) to raise.
    mock_idaapi = MagicMock()
    mock_idaapi.msg.side_effect = RuntimeError("IDA shutting down")
    with patch.dict("sys.modules", {"idaapi": mock_idaapi}):
        with patch("sys.stderr.write") as mock_write:
            handler.emit(record)
            mock_write.assert_called_once()
            written = mock_write.call_args[0][0]
            assert "test message" in written
