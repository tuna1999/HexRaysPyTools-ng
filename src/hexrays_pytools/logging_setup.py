"""Centralized logging configuration for HexRaysPyTools.

Configures the root logger to emit either to the IDA Output window
(when running inside IDA, via ``idaapi.msg``) or to stderr (when running
in the mock/test environment). Called once during plugin init via
``setup_logging(session.log_level)``.
"""
from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "[HexRaysPyTools][%(levelname)s] %(message)s (%(module)s:%(funcName)s:%(lineno)d)"


class IdaOutputHandler(logging.Handler):
    """Emit log records to the IDA Output window via ``idaapi.msg``.

    Used when the plugin runs inside IDA. In the mock/test environment
    ``idaapi.msg`` does not exist (or is a Mock), so the fallback
    StreamHandler is used instead — see ``_make_handler``.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            import idaapi  # type: ignore[import-not-found]

            idaapi.msg(self.format(record) + "\n")
        except Exception:
            # If idaapi.msg fails (e.g., IDA shutting down), fall back
            # to stderr rather than crashing the plugin.
            sys.stderr.write(self.format(record) + "\n")


def _ida_output_available() -> bool:
    """Return True if we are running inside real IDA (not the mock).

    The mock's ``idaapi.msg`` is a ``MagicMock`` callable; the real one
    is a SWIG builtin function. We detect the real one by checking that
    ``idaapi`` is importable and ``msg`` is callable but NOT a Mock
    instance.
    """
    try:
        from unittest.mock import Mock

        import idaapi

        return callable(idaapi.msg) and not isinstance(idaapi.msg, Mock)
    except ImportError:
        return False


def _make_handler() -> logging.Handler:
    """Return the appropriate handler for the current environment."""
    if _ida_output_available():
        return IdaOutputHandler()
    return logging.StreamHandler()


def setup_logging(level: int) -> None:
    """Configure the root logger. Idempotent.

    Removes any previously-installed HexRaysPyTools handlers before
    adding a fresh one — so re-calling ``setup_logging`` (e.g., after a
    ``log_level`` setting change + plugin reload) does not stack handlers.
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Remove our previous handlers to avoid duplicates on re-init.
    for h in list(root.handlers):
        if getattr(h, "_hexrays_pytools", False):
            root.removeHandler(h)

    handler = _make_handler()
    handler._hexrays_pytools = True  # type: ignore[attr-defined]
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(handler)
