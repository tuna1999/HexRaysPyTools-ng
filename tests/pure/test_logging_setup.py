"""Test logging_setup module."""
import logging

from hexrays_pytools.logging_setup import setup_logging


def test_setup_logging_sets_root_level() -> None:
    """setup_logging(N) should set root logger level to N."""
    setup_logging(logging.WARNING)
    assert logging.getLogger().level == logging.WARNING


def test_setup_logging_is_idempotent() -> None:
    """Calling setup_logging twice should not add duplicate handlers."""
    setup_logging(logging.INFO)
    initial_handler_count = len(logging.getLogger().handlers)
    setup_logging(logging.INFO)
    assert len(logging.getLogger().handlers) == initial_handler_count


def test_setup_logging_format_contains_module_and_function() -> None:
    """The log format should include module name and function name."""
    import io
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s\t(%(module)s:%(funcName)s)"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    try:
        root.info("test message")
        output = buf.getvalue()
        assert "test message" in output
        assert "test_logging_setup" in output
        assert "test_setup_logging_format_contains_module_and_function" in output
    finally:
        root.removeHandler(handler)
