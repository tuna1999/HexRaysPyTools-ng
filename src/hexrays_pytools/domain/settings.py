"""HCLI settings wrapper.

Reads settings stored by the HCLI plugin installer into `ida_settings`,
mapping them onto the Session dataclass. Replaces the original `.cfg` file
parser in `settings.py`.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import ida_settings  # type: ignore[import-not-found]

if TYPE_CHECKING:
    from .session import Session

logger = logging.getLogger(__name__)

SETTING_KEYS: tuple[str, ...] = (
    "log_level",
    "propagate_through_all_names",
    "store_xrefs",
    "scan_any_type",
    "templated_types_file",
)


def load_into(session: Session) -> None:
    """Read HCLI settings into session fields.

    Each setting that returns a value is applied; None values are skipped
    (the user did not configure that setting in HCLI).
    """
    for key in SETTING_KEYS:
        try:
            raw = ida_settings.get_current_plugin_setting(key)
        except Exception as e:  # noqa: BLE001 — HCLI may not be initialized
            logger.debug("ida_settings not available for %s: %s", key, e)
            continue
        if raw is None:
            continue
        _apply(session, key, raw)


def _apply(session: Session, key: str, raw: object) -> None:
    match key:
        case "log_level":
            session.log_level = getattr(logging, str(raw).upper(), logging.INFO)
        case "propagate_through_all_names":
            session.propagate_through_all_names = bool(raw)
        case "store_xrefs":
            session.store_xrefs = bool(raw)
        case "scan_any_type":
            session.scan_any_type = bool(raw)
        case "templated_types_file":
            session.templated_types_file = str(raw)
        case _:
            logger.debug("Unknown setting key: %s", key)
