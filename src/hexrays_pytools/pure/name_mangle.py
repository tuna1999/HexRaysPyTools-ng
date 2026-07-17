"""Sanitize demangled C++ names to C-legal identifiers.

Pure function — no IDA dependency. Replaces the original `demangled_name_to_c_str`
in `HexRaysPyTools/core/common.py` with explicit, well-tested behavior.
"""

from __future__ import annotations

import re

# Characters that are NOT legal in a C identifier
# NOTE: the original common.py used `:::+` (3+ colons), which never matched the
# `::` namespace separator. Fixed to `::+` so rule #2 (`::` -> `_`) holds.
_ILLEGAL_CHARS = re.compile(r"::+|(?=:(?=[^:]))(?=(?<=[^:]):):|^:[^:]|[^:]:$|^:$|[^a-zA-Z_0-9:]")
# NOTE: comma between template args (e.g. `map<string,int>`) is mapped to `_t_`
# so each argument stays delimited, matching the documented test expectation.


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
    # Replace comma between template args so each argument stays delimited
    name = name.replace(",", "_t_")
    # Collapse illegal character runs and split on remaining colons
    return "_".join(filter(len, _ILLEGAL_CHARS.split(name)))
