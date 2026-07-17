"""Parse and render C++ templated types defined in TOML.

Pure module — no IDA dependency. Replaces `core/templated_types.py` with explicit
validation and the stdlib `tomllib` (Python 3.11+).

The TOML format expects:
    ["pretty::TypeName<T>"]
    base_name = "ida_type_{1}"        # format string for IDA's struct name
    types = ["T"]                     # list of type-parameter names
    struct = "struct ida_type_{1} {{ {0} field; }};"  # C-like declaration

Format tokens: for N type params, `args` is a flat list of 2*N entries
interleaved as [actual_0, pretty_0, actual_1, pretty_1, ...]. Actual types (even
indices) are mangled to C-legal identifiers via `_to_field_type`; pretty tokens
(odd indices) are C-legal identifiers used in `base_name` and inside `struct`.
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


def _to_field_type(actual: str) -> str:
    """Mangle an "actual" C++ type token into a C-legal field-type identifier.

    Rules (minimal, sufficient for templated struct field names):
      1. `*` (pointer) is replaced with `_PTR`.
      2. Internal spaces are stripped.

    Examples:
        "int"    -> "int"
        "int *"  -> "int_PTR"
        "char *" -> "char_PTR"
    """
    return actual.replace("*", "_PTR").replace(" ", "")


def parse_toml_template(content: str) -> Result[TemplateDict, str]:
    """Parse TOML content into a dict of templated type definitions.

    Returns Result.ok(dict) on success, Result.err(message) on parse failure.
    """
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError as e:
        return Result.err(f"TOML parse error: {e}")
    return Result.ok(data)


def render_template(template: TemplateDef, args: list[str]) -> Result[tuple[str, str], str]:
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
    # `args` interleaves [actual_0, pretty_0, actual_1, pretty_1, ...].
    # Even indices (actual types) are mangled to C-legal identifiers so they are
    # usable as struct field types / names (e.g. "int *" -> "int_PTR").
    # Odd indices (pretty identifiers) are already C-legal and pass through.
    mangled = [_to_field_type(a) if i % 2 == 0 else a for i, a in enumerate(args)]
    try:
        type_name = template["base_name"].format(*mangled)
        c_decl = template["struct"].format(*mangled)
    except (IndexError, KeyError) as e:
        return Result.err(f"format token error: {e}")
    return Result.ok((type_name, c_decl))
