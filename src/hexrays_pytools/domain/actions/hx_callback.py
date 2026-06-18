"""Manage hxe_* (Hex-Rays decompiler) callbacks."""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

import idaapi  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


class HxCallbackManager:
    """Installs/removes a Hex-Rays callback dispatcher."""

    def __init__(self) -> None:
        self._handlers: dict = defaultdict(list)  # type: ignore[type-arg]
        self._installed = False

    def install(self) -> None:
        if self._installed:
            return
        idaapi.install_hexrays_callback(self._dispatch)
        self._installed = True

    def register(self, event_id: int, handler: Any) -> None:
        """Register a handler for `event_id`."""
        self._handlers[event_id].append(handler)

    def _dispatch(self, event: int, *args: Any) -> int:
        for handler in self._handlers.get(event, []):
            try:
                handler.handle(event, *args)
            except Exception as e:  # noqa: BLE001
                logger.exception("HxCallback handler failed: %s", e)
        return 0

    def detach_all(self) -> None:
        if self._installed:
            idaapi.remove_hexrays_callback(self._dispatch)
            self._installed = False
        self._handlers.clear()
