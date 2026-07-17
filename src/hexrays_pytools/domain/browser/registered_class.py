"""Class — a struct/class with virtual tables, registered in Local Types.

Extracted from `core/classes.py:Class`. Represents a single class discovered
in Local Types that has one or more vtable fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import idaapi  # type: ignore[import-not-found]


@dataclass
class Class:
    """A struct/class with vtable fields."""

    name: str
    ordinal: int = 0
    tinfo: Any = None
    vtables: dict[int, Any] = field(default_factory=dict)  # offset -> RegisteredVTable
    selected: bool = False

    @staticmethod
    def create(ordinal: int) -> Class | None:
        """Factory: read a Local Type and return a Class if it has a vtable field.

        Returns None if the type is not a class with vtables.
        """
        tinfo = idaapi.tinfo_t()
        tinfo.get_numbered_type(idaapi.get_idati(), ordinal)
        if not tinfo or not tinfo.is_udt():
            return None
        udt = idaapi.udt_type_data_t()
        tinfo.get_udt_details(udt)
        # Heuristic: if any field is a ptr-to-struct-of-funcptrs, it's a vtable
        has_vtable = False
        for member in udt:
            mt = member.type
            if mt.is_ptr():
                pointed = mt.get_pointed_object()
                if pointed and pointed.is_funcptr():
                    has_vtable = True
                    break
        if not has_vtable:
            return None
        return Class(
            name=str(tinfo.dstr()) if hasattr(tinfo, "dstr") else "",
            ordinal=ordinal,
            tinfo=tinfo,
        )

    def has_function(self, name_regex: str) -> bool:
        """Return True if any vtable contains a function matching `name_regex`."""
        import re

        for vtable in self.vtables.values():
            for vf in getattr(vtable, "virtual_functions", []):
                if re.search(name_regex, getattr(vf, "name", "")):
                    return True
        return False
