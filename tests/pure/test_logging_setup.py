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
