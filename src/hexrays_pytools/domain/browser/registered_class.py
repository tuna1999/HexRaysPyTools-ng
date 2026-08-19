"""Class — a struct/class with virtual tables, registered in Local Types.

Extracted from `core/classes.py:Class`. Represents a single class discovered
in Local Types that has one or more vtable fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import idaapi  # type: ignore[import-not-found]

from .registered_vtable import RegisteredVTable


@dataclass
class Class:
    """A struct/class with vtable fields."""

    name: str
    ordinal: int = 0
    tinfo: Any = None
    vtables: dict[int, Any] = field(default_factory=dict)  # offset -> RegisteredVTable
    selected: bool = False
    modified: bool = False
    demangled_names: dict[str, set[int]] = field(default_factory=dict, repr=False)

    @staticmethod
    def create(
        ordinal: int,
        demangled_names: dict[str, set[int]] | None = None,
    ) -> Class | None:
        """Factory: read a Local Type and return a Class if it has a vtable field.

        Returns None if the type is not a class with vtables.
        """
        tinfo = idaapi.tinfo_t()
        tinfo.get_numbered_type(idaapi.get_idati(), ordinal)
        if not tinfo or not tinfo.is_udt():
            return None
        udt = idaapi.udt_type_data_t()
        tinfo.get_udt_details(udt)
        vtables: dict[int, RegisteredVTable] = {}
        for member in udt:
            mt = member.type
            if not mt.is_ptr():
                continue
            pointed = mt.get_pointed_object()
            if not pointed or not pointed.is_udt():
                continue
            v_udt = idaapi.udt_type_data_t()
            if not pointed.get_udt_details(v_udt) or len(v_udt) == 0:
                continue
            if not all(func.type.is_funcptr() for func in v_udt):
                continue

            vt_ordinal = int(pointed.get_ordinal())
            if vt_ordinal == 0:
                vt_ordinal = int(idaapi.get_type_ordinal(idaapi.get_idati(), str(pointed.dstr())))
            if vt_ordinal == 0:
                imported = int(
                    idaapi.import_type(idaapi.get_idati(), -1, str(pointed.dstr()), 0)
                )
                if imported != int(idaapi.BADNODE):
                    vt_ordinal = int(
                        idaapi.get_type_ordinal(idaapi.get_idati(), str(pointed.dstr()))
                    )
            vtable = RegisteredVTable(
                name=str(pointed.dstr()),
                ordinal=vt_ordinal,
                tinfo=pointed,
                offset=int(member.offset) // 8,
            )
            vtable.class_name = str(tinfo.dstr())
            vtable.populate_virtual_functions(demangled_names)
            vtables[int(member.offset) // 8] = vtable

        if not vtables:
            return None
        cls = Class(
            name=str(tinfo.dstr()) if hasattr(tinfo, "dstr") else "",
            ordinal=ordinal,
            tinfo=tinfo,
            vtables=vtables,
            demangled_names=demangled_names or {},
        )
        for vtable in cls.vtables.values():
            vtable.class_ = [cls]
        return cls

    def update_from_local_types(self) -> None:
        if not self.modified:
            return
        fresh = self.create(self.ordinal, self.demangled_names)
        if fresh is None:
            return
        self.name = fresh.name
        self.tinfo = fresh.tinfo
        self.vtables = fresh.vtables
        self.modified = False

    def update_local_type(self) -> None:
        if not self.modified:
            return
        for vtable in self.vtables.values():
            vtable.update_local_type()
        try:
            udt_data = idaapi.udt_type_data_t()
            self.tinfo.get_udt_details(udt_data)
            final_tinfo = idaapi.tinfo_t()
            if final_tinfo.create_udt(udt_data, idaapi.BTF_STRUCT):
                final_tinfo.set_numbered_type(
                    idaapi.get_idati(),
                    int(self.ordinal),
                    idaapi.NTF_REPLACE,
                    self.name,
                )
                self.tinfo = final_tinfo
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return
        self.modified = False

    def set_first_argument_type(self, class_name: str) -> None:
        if 0 in self.vtables:
            self.vtables[0].set_first_argument_type(class_name)

    def data(self, column: int) -> Any:
        if column == 0:
            return self.name
        return None

    def setData(self, column: int, value: str) -> bool:  # noqa: N802 - Qt model contract
        if column == 0 and bool(idaapi.is_ident(str(value))) and self.name != value:
            self.name = str(value)
            self.modified = True
            return True
        return False

    def flags(self, column: int) -> Any:
        from PySide6 import QtCore

        if column == 0:
            return (
                QtCore.Qt.ItemFlag.ItemIsSelectable
                | QtCore.Qt.ItemFlag.ItemIsEditable
                | QtCore.Qt.ItemFlag.ItemIsEnabled
            )
        return QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled

    def font(self, column: int) -> Any:
        from PySide6 import QtGui

        return QtGui.QFont("Consolas", 12, QtGui.QFont.Weight.Bold, italic=self.modified)

    @property
    def color(self) -> Any:
        from PySide6 import QtGui

        return QtGui.QColor("#80ced6")

    def tooltip(self) -> str:
        return self.name

    @property
    def children(self) -> list[Any]:
        return list(self.vtables.values())

    def has_function(self, name_regex: str) -> bool:
        """Return True if any vtable contains a function matching `name_regex`."""
        import re

        for vtable in self.vtables.values():
            for vf in getattr(vtable, "virtual_functions", []):
                if re.search(name_regex, getattr(vf, "name", "")):
                    return True
        return False
