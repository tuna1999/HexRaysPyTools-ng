# Task 2.12 Brief: domain/templated/templated_types.py + data

## Files (5)
1. `src/hexrays_pytools/domain/templated/__init__.py` (empty)
2. `src/hexrays_pytools/domain/templated/templated_types.py`
3. `src/hexrays_pytools/domain/templated/data/templated_types.toml`
4. `tests/domain/templated/__init__.py` (empty)
5. `tests/domain/templated/test_templated_types.py`

## `templated_types.py` (verbatim)

```python
"""Templated types loader — wraps pure/toml_template.

Replaces `core/templated_types.py`. Loads C++ templated type definitions
from a TOML file (default: bundled, custom: from session.templated_types_file).
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any

from ...pure.toml_template import parse_toml_template, render_template
from ...pure.result import Result

logger = logging.getLogger(__name__)

# Path to bundled templated types TOML
_BUNDLED_PATH = Path(__file__).parent / "data" / "templated_types.toml"


class TemplatedTypes:
    """Manages the C++ templated type definitions."""

    def __init__(self, custom_path: str = "") -> None:
        self._path = Path(custom_path) if custom_path else _BUNDLED_PATH
        self._types: dict = {}
        self._keys: list[str] = []
        self.reload_types()

    def reload_types(self) -> None:
        """Reload types from the configured path."""
        result = parse_toml_template(self._path.read_text())
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
        return self._types[key].get("types", [])

    @property
    def keys(self) -> list[str]:
        """List all available template keys."""
        return list(self._keys)
```

## `data/templated_types.toml` (minimal, copies from refs/.../types/)

```toml
["std::vector<T>"]
base_name = "std_vector_{1}"
types = ["T"]
struct = """
struct std_vector_{1} {{
    {0} *_Myfirst;
    {0} *_Mylast;
    {0} *_Myend;
}};
"""
```

Create `data/` subdir; add `data/__init__.py` (empty) to make it a package.

## `test_templated_types.py` (verbatim)

```python
"""Test TemplatedTypes."""
from hexrays_pytools.domain.templated.templated_types import TemplatedTypes


def test_load_bundled_types() -> None:
    """Default construction loads bundled templated types."""
    t = TemplatedTypes()
    assert "std::vector<T>" in t.keys


def test_custom_path_missing_file() -> None:
    """Custom path that doesn't exist results in empty keys."""
    t = TemplatedTypes(custom_path="/nonexistent/path.toml")
    assert t.keys == []


def test_get_types_for_known_key() -> None:
    """get_types returns the type-param list for a known key."""
    t = TemplatedTypes()
    types = t.get_types("std::vector<T>")
    assert types == ["T"]


def test_get_types_for_unknown_key() -> None:
    """get_types returns None for an unknown key."""
    t = TemplatedTypes()
    assert t.get_types("std::unknown<X>") is None


def test_get_decl_str_renders_template() -> None:
    """get_decl_str returns (name, decl) for valid args."""
    t = TemplatedTypes()
    result = t.get_decl_str("std::vector<T>", ["int *", "pInt"])
    assert result.is_ok
    name, decl = result.unwrap()
    assert name == "std_vector_pInt"
    assert "int_PTR *_Myfirst" in decl


def test_get_decl_str_unknown_key() -> None:
    """get_decl_str returns err for unknown key."""
    t = TemplatedTypes()
    result = t.get_decl_str("std::unknown<X>", ["T", "pT"])
    assert not result.is_ok
```

## Verification
```bash
PYTHONPATH=src pytest tests/domain/templated/test_templated_types.py -v
python -m mypy --strict src/hexrays_pytools/domain/templated/
python -m ruff check src/hexrays_pytools/domain/templated/ tests/domain/templated/
```

## Commit
```bash
git add src/hexrays_pytools/domain/templated/ tests/domain/templated/
git commit -m "feat(templated): add TemplatedTypes loader (wraps pure/toml_template)"
```

## Report
`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.12-report.md`