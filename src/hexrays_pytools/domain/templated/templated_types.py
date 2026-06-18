"""Templated types loader — wraps pure/toml_template.

Replaces `core/templated_types.py`. Loads C++ templated type definitions
from a TOML file (default: bundled, custom: from session.templated_types_file).
"""
from __future__ import annotations

import logging
from pathlib import Path

from ...pure.result import Result
from ...pure.toml_template import TemplateDef, parse_toml_template, render_template

logger = logging.getLogger(__name__)

# Path to bundled templated types TOML
_BUNDLED_PATH = Path(__file__).parent / "data" / "templated_types.toml"


class TemplatedTypes:
    """Manages the C++ templated type definitions."""

    def __init__(self, custom_path: str = "") -> None:
        self._path = Path(custom_path) if custom_path else _BUNDLED_PATH
        self._types: dict[str, TemplateDef] = {}
        self._keys: list[str] = []
        self.reload_types()

    def reload_types(self) -> None:
        """Reload types from the configured path.

        Missing or unreadable files leave the type map empty rather than raising,
        so callers can degrade gracefully (e.g. an unconfigured custom path).
        """
        try:
            content = self._path.read_text()
        except OSError as e:
            logger.error("Failed to read templated types file %s: %s", self._path, e)
            self._types = {}
            self._keys = []
            return
        result = parse_toml_template(content)
        if not result.is_ok:
            logger.error("Failed to load templated types: %s", result.error)
            return
        self._types = result.unwrap()
        self._keys = list(self._types.keys())

    def get_decl_str(self, key: str, args: list[str]) -> Result[tuple[str, str], str]:
        """Render a template by key with the given args (2*N format)."""
        if key not in self._types:
            return Result.err(f"type not in type dictionary: {key}")
        return render_template(self._types[key], args)

    def get_types(self, key: str) -> list[str] | None:
        """Get the type-param names for a template, or None if not found."""
        if key not in self._types:
            return None
        types = self._types[key].get("types", [])
        # Narrow to list[str]; TOML values are Any but the schema guarantees a list.
        return list(types)

    @property
    def keys(self) -> list[str]:
        """List all available template keys."""
        return list(self._keys)
