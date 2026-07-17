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
        # F4: record last N exceptions from handlers. Read-only access via
        # Session.recent_callback_errors. Helps surface silent handler failures
        # to UI / status bar (rendering is follow-up scope).
        self.errors: list[tuple[int, Exception]] = []  # F4: (event_id, exception) pairs

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
            except Exception as e:  # noqa: BLE001 — intentional swallow to prevent native crash
                logger.exception("HxCallback handler failed: %s", e)
                # F4: record exception for visibility (UI can poll via
                # Session.recent_callback_errors). Keep last 100 to bound memory.
                self.errors.append((event, e))
                if len(self.errors) > 100:
                    self.errors.pop(0)
        return 0

    def detach_all(self) -> None:
        if self._installed:
            idaapi.remove_hexrays_callback(self._dispatch)
            self._installed = False
        self._handlers.clear()
