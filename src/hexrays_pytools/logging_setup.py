"""Centralized logging configuration for HexRaysPyTools.

Replaces the original `logging.basicConfig(...)` call in `PLUGIN_ENTRY`.
Use `setup_logging(level)` once during plugin init.
"""
import logging

_LOG_FORMAT = "[%(levelname)s] %(message)s\t(%(module)s:%(funcName)s)"


def setup_logging(level: int) -> None:
    """Configure the root logger with our standard format.

    Idempotent: safe to call multiple times (does not add duplicate handlers).
    """
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(handler)
