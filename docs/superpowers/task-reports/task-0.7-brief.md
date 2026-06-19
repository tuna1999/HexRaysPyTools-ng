# Task 0.7 Brief: pure/toml_template.py

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\pure\toml_template.py`
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\pure\test_toml_template.py`
3. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\fixtures\__init__.py` (empty)
4. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\fixtures\sample_templated_types.toml`

## Required Content (verbatim)

### `src/hexrays_pytools/pure/toml_template.py`

```python
"""Parse and render C++ templated types defined in TOML.

Pure module — no IDA dependency. Replaces `core/templated_types.py` with explicit
validation and the stdlib `tomllib` (Python 3.11+).

The TOML format expects:
    ["pretty::TypeName<T>"]
    base_name = "ida_type_{1}"        # format string for IDA's struct name
    types = ["T"]                     # list of type-parameter names
    struct = "struct ida_type_{1} {{ {0} field; }};"  # C-like declaration

Format tokens: for N type params, tokens 0..N-1 are actual types and tokens N..2N-1
are "pretty print" tokens (used in `base_name` and inside `struct` for unique IDs).
"""
from __future__ import annotations
import tomllib
from typing import TypedDict

from .result import Result


class TemplateDef(TypedDict):
    """Schema for a single templated type entry."""
    base_name: str
    types: list[str]
    struct: str


# Parse result is dict[str, TemplateDef]
TemplateDict = dict[str, TemplateDef]


def parse_toml_template(content: str) -> Result[TemplateDict, str]:
    """Parse TOML content into a dict of templated type definitions.

    Returns Result.ok(dict) on success, Result.err(message) on parse failure.
    """
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError as e:
        return Result.err(f"TOML parse error: {e}")
    return Result.ok(data)


def render_template(
    template: TemplateDef, args: list[str]
) -> Result[tuple[str, str], str]:
    """Render a template with the given type arguments.

    `args` is a flat list: [actual_type_0, pretty_0, actual_type_1, pretty_1, ...]
    Length must be exactly 2 * len(template["types"]).

    Returns Result.ok((type_name, c_decl)) on success, Result.err(msg) on mismatch.
    """
    n = len(template["types"])
    if len(args) != 2 * n:
        return Result.err(
            f"arg count mismatch: expected {2 * n} (for {n} type params), got {len(args)}"
        )
    try:
        type_name = template["base_name"].format(*args)
        c_decl = template["struct"].format(*args)
    except (IndexError, KeyError) as e:
        return Result.err(f"format token error: {e}")
    return Result.ok((type_name, c_decl))
```

### `tests/fixtures/sample_templated_types.toml`

```toml
["std::vector<T>"]
base_name = "std_vector_{1}"
types = ["T"]
struct = """
struct std_vector_{1} {
    {0} *_Myfirst;
    {0} *_Mylast;
    {0} *_Myend;
};
"""

["std::map<K,V>"]
base_name = "std_map_{1}_{3}"
types = ["K", "V"]
struct = """
struct std_pair_{1}_{3} {
    {0} first;
    {2} second;
};
struct std_map_{1}_{3} {
    std_pair_{1}_{3} *_Myhead;
    unsigned long long _Mysize;
};
"""
```

### `tests/pure/test_toml_template.py`

```python
"""Test toml_template.parse_toml_template and render_template."""
from pathlib import Path
from hexrays_pytools.pure.toml_template import parse_toml_template, render_template

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_templated_types.toml"


def test_parse_valid_toml() -> None:
    """Valid TOML is parsed into a dict of templates."""
    result = parse_toml_template(FIXTURE.read_text())
    assert result.is_ok
    templates = result.unwrap()
    assert "std::vector<T>" in templates
    assert "std::map<K,V>" in templates


def test_parse_invalid_toml_returns_err() -> None:
    """Malformed TOML returns an error result."""
    result = parse_toml_template("not valid toml [[[")
    assert not result.is_ok
    assert result.error is not None


def test_render_single_param_template() -> None:
    """A template with 1 type param renders correctly with 2 args (actual, pretty)."""
    result = parse_toml_template(FIXTURE.read_text())
    templates = result.unwrap()
    rendered = render_template(templates["std::vector<T>"], ["int *", "pInt"])
    assert rendered.is_ok
    type_name, decl = rendered.unwrap()
    assert type_name == "std_vector_pInt"
    assert "int_PTR *_Myfirst" in decl


def test_render_two_param_template() -> None:
    """A template with 2 type params renders correctly with 4 args (actual, pretty, actual, pretty)."""
    result = parse_toml_template(FIXTURE.read_text())
    templates = result.unwrap()
    rendered = render_template(templates["std::map<K,V>"], ["int", "pInt", "char *", "pChar"])
    assert rendered.is_ok
    type_name, decl = rendered.unwrap()
    assert type_name == "std_map_pInt_pChar"
    assert "int first" in decl
    assert "char_PTR second" in decl


def test_render_wrong_arg_count_returns_err() -> None:
    """Wrong number of args returns an error."""
    result = parse_toml_template(FIXTURE.read_text())
    templates = result.unwrap()
    rendered = render_template(templates["std::vector<T>"], ["int *", "pInt", "extra"])
    assert not rendered.is_ok


def test_render_unknown_template_returns_err() -> None:
    """Render with 0 args (need 2) returns an error."""
    result = parse_toml_template(FIXTURE.read_text())
    templates = result.unwrap()
    rendered = render_template(templates["std::vector<T>"], [])
    assert not rendered.is_ok
```

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/pure/test_toml_template.py -v
python -m mypy --strict src/hexrays_pytools/pure/toml_template.py
python -m ruff check src/hexrays_pytools/pure/toml_template.py tests/pure/test_toml_template.py tests/fixtures/
```

## Commit

```bash
git add src/hexrays_pytools/pure/toml_template.py tests/pure/test_toml_template.py tests/fixtures/
git commit -m "feat(pure): add toml_template parser/renderer (stdlib tomllib)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-0.7-report.md`
