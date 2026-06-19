# Task 0.5 Brief: pure/name_mangle.py

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\pure\name_mangle.py`
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\pure\test_name_mangle.py`

## Required Content (verbatim)

### `src/hexrays_pytools/pure/name_mangle.py`

```python
"""Sanitize demangled C++ names to C-legal identifiers.

Pure function — no IDA dependency. Replaces the original `demangled_name_to_c_str`
in `HexRaysPyTools/core/common.py` with explicit, well-tested behavior.
"""
from __future__ import annotations
import re

# Characters that are NOT legal in a C identifier
_ILLEGAL_CHARS = re.compile(r":::+|(?=:(?=[^:]))(?=(?<=[^:]):):|^:[^:]|[^:]:$|^:$|[^a-zA-Z_0-9:]")


def sanitize_c_name(name: str) -> str:
    """Convert a demangled C++ symbol name into a C-legal identifier.

    Examples:
        "std::vector<int*>" -> "std_vector_t_int_PTR_t_"
        "~MyClass"          -> "DESTRUCTOR_MyClass"
        "`vtable for Foo"   -> "`vtable for Foo"  (preserved as-is)

    Rules:
        1. Names starting with backtick are returned unchanged (vtable/typeinfo).
        2. `::` is replaced with `_` (namespace separator).
        3. `*` (pointer) is replaced with `_PTR`.
        4. `<` and `>` (templates) are replaced with `_t_`.
        5. `~` (destructor) is replaced with `DESTRUCTOR_`.
        6. `public:`, `protected:`, `private:` access keywords are stripped.
        7. Other illegal characters are stripped or replaced.
    """
    if not name:
        return ""
    # Preserve `vtable and `typeinfo names (backtick prefix)
    if name.startswith("`"):
        return name
    # Strip access keywords
    name = name.replace("public:", "").replace("protected:", "").replace("private:", "")
    # Replace destructor prefix
    name = name.replace("~", "DESTRUCTOR_")
    # Replace pointer suffix
    name = name.replace("*", "_PTR")
    # Replace template angle brackets
    name = name.replace("<", "_t_").replace(">", "_t_")
    # Collapse illegal character runs and split on remaining colons
    name = "_".join(filter(len, _ILLEGAL_CHARS.split(name)))
    return name
```

### `tests/pure/test_name_mangle.py`

```python
"""Test name_mangle.sanitize_c_name."""
from hexrays_pytools.pure.name_mangle import sanitize_c_name


def test_simple_name_unchanged() -> None:
    """Names that are already valid C identifiers pass through unchanged."""
    assert sanitize_c_name("foo") == "foo"
    assert sanitize_c_name("MyClass") == "MyClass"
    assert sanitize_c_name("foo_bar123") == "foo_bar123"


def test_colon_colon_replaced_with_underscore() -> None:
    """`::` namespace separator is replaced with `_`."""
    assert sanitize_c_name("std::vector") == "std_vector"
    assert sanitize_c_name("a::b::c") == "a_b_c"


def test_pointer_suffix_replaced() -> None:
    """`*` pointer suffix is replaced with `_PTR`."""
    assert sanitize_c_name("int*") == "int_PTR"
    assert sanitize_c_name("MyClass**") == "MyClass_PTR_PTR"


def test_template_angle_brackets_replaced() -> None:
    """`<` and `>` template brackets are replaced with `_t_`."""
    assert sanitize_c_name("std::vector<int>") == "std_vector_t_int_t_"
    assert sanitize_c_name("map<string,int>") == "map_t_string_t_int_t_"


def test_destructor_tilde_replaced() -> None:
    """`~` destructor prefix is replaced with `DESTRUCTOR_`."""
    assert sanitize_c_name("~MyClass") == "DESTRUCTOR_MyClass"


def test_access_keywords_stripped() -> None:
    """`public:`, `protected:`, `private:` are stripped."""
    assert sanitize_c_name("public:foo") == "foo"
    assert sanitize_c_name("protected:bar") == "bar"
    assert sanitize_c_name("private:baz") == "baz"


def test_vtable_and_typeinfo_prefix_preserved() -> None:
    """Names starting with backtick are preserved as-is."""
    assert sanitize_c_name("`vtable for Foo") == "`vtable for Foo"
    assert sanitize_c_name("`typeinfo for Bar") == "`typeinfo for Bar"


def test_empty_string_returns_empty() -> None:
    """Empty input returns empty output."""
    assert sanitize_c_name("") == ""


def test_illegal_chars_replaced_with_underscore() -> None:
    """Other illegal characters are replaced or stripped."""
    assert "::" not in sanitize_c_name("foo:::bar")
```

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/pure/test_name_mangle.py -v
# RED first, then GREEN: 9 tests pass
python -m mypy --strict src/hexrays_pytools/pure/name_mangle.py
python -m ruff check src/hexrays_pytools/pure/name_mangle.py tests/pure/test_name_mangle.py
```

## Commit

```bash
git add src/hexrays_pytools/pure/name_mangle.py tests/pure/test_name_mangle.py
git commit -m "feat(pure): add name_mangle.sanitize_c_name (replaces common.py)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-0.5-report.md`
