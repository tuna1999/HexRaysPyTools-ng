"""Discovered vtable — found during struct reconstruction.

Renamed from `core/temporary_structure.VirtualTable` to avoid collision
with `core/classes.VirtualTable` (a different concept: a registered vtable
in Local Types).
"""

from __future__ import annotations

import logging
import re
from contextlib import suppress
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import idaapi  # type: ignore[import-not-found]
import idc  # type: ignore[import-not-found]

from ...infra.arch.arch import get_ptr, is_code_ea, is_imported_ea
from .member import AbstractMember

logger = logging.getLogger(__name__)


@dataclass
class VirtualFunction:
    """A single virtual function entry in a vtable."""

    offset: int
    tinfo: Any = None
    name: str = ""
    func_ea: int = 0
    visited: bool = False

    def show_location(self) -> None:
        try:
            idaapi.open_pseudocode(int(self.func_ea), 1)
        except (AttributeError, RuntimeError):
            idaapi.jumpto(int(self.func_ea))


@dataclass
class ImportedVirtualFunction:
    """Virtual function imported from a type library (no decompile)."""

    offset: int
    tinfo: Any = None
    name: str = ""
    func_ea: int = 0
    visited: bool = False

    def show_location(self) -> None:
        idaapi.jumpto(int(self.func_ea))


@dataclass
class DiscoveredVTable(AbstractMember):
    """A vtable discovered while scanning a struct.

    A working copy — different from the registered vtable in Local Types
    (see `domain/browser/registered_vtable.py`).
    """

    address: int = 0
    virtual_functions: list[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Same coordinate system as Member/VoidMember: scanner supplies a
        # relative offset and ``origin`` identifies the containing subobject.
        self.offset = int(self.offset) + int(self.origin)

    def populate(self) -> None:
        """Read the table and build typed virtual-function entries.

        This restores the v1 Structure Builder workflow where double-clicking
        a discovered vtable exposes its methods and lets the user scan them.
        """
        self.virtual_functions = []
        ea = self._table_address()
        if not ea:
            return
        ptr_size = 8 if idaapi.inf_is_64bit() else 4
        current = ea
        for _ in range(256):
            try:
                ptr = get_ptr(current)
            except (RuntimeError, TypeError, ValueError):
                break
            if not ptr:
                break
            offset = current - ea
            if is_imported_ea(ptr, set()):
                tinfo = idaapi.tinfo_t()
                with suppress(AttributeError, RuntimeError):
                    idaapi.guess_tinfo(tinfo, int(ptr))
                raw_name = idaapi.get_name(int(ptr))
                func_name = raw_name if isinstance(raw_name, str) and raw_name else f"sub_{int(ptr):X}"
                self.virtual_functions.append(
                    ImportedVirtualFunction(
                        offset=offset,
                        tinfo=tinfo,
                        name=func_name,
                        func_ea=int(ptr),
                    )
                )
            elif is_code_ea(ptr):
                tinfo = None
                try:
                    cfunc = idaapi.decompile(int(ptr))
                    if cfunc is not None and getattr(cfunc, "type", None) is not None:
                        tinfo = idaapi.tinfo_t(cfunc.type)
                except (AttributeError, RuntimeError, idaapi.DecompilationFailure):
                    pass
                raw_name = idaapi.get_name(int(ptr))
                func_name = raw_name if isinstance(raw_name, str) and raw_name else f"sub_{int(ptr):X}"
                self.virtual_functions.append(
                    VirtualFunction(
                        offset=offset,
                        tinfo=tinfo,
                        name=func_name,
                        func_ea=int(ptr),
                    )
                )
            else:
                break
            current += ptr_size

    def scan_virtual_function(self, index: int, workspace: Any) -> None:
        """Deep-scan the first argument of one virtual function into workspace."""
        if not (0 <= int(index) < len(self.virtual_functions)):
            return
        entry = self.virtual_functions[int(index)]
        if isinstance(entry, ImportedVirtualFunction):
            logger.info("Ignoring imported virtual function at 0x%X", entry.func_ea)
            return
        try:
            cfunc = idaapi.decompile(int(entry.func_ea))
        except (AttributeError, RuntimeError, idaapi.DecompilationFailure):
            logger.warning("Failed to decompile virtual function at 0x%X", entry.func_ea)
            return
        if cfunc is None:
            return
        args = list(getattr(cfunc, "arguments", []))
        lvars = list(cfunc.get_lvars()) if hasattr(cfunc, "get_lvars") else []
        if not args or not lvars:
            return

        from ..const import init_consts
        from ..scanner.member_extractor import NewDeepSearchVisitor
        from ..scanner.scanned_object import VariableObject

        obj = VariableObject(lvars[0], 0)
        target_workspace = workspace
        if not hasattr(target_workspace, "model"):
            target_workspace = SimpleNamespace(model=workspace)
        NewDeepSearchVisitor(
            cfunc,
            int(self.offset),
            obj,
            target_workspace,
            consts=init_consts(),
        ).process()
        entry.visited = True

    def scan_virtual_functions(self, workspace: Any) -> None:
        for index in range(len(self.virtual_functions)):
            self.scan_virtual_function(index, workspace)

    def activate(self, model: Any) -> None:
        """Open a chooser for virtual functions, matching the original UX."""
        if not self.virtual_functions:
            self.populate()
        if not self.virtual_functions:
            return

        from ..chooser import MyChoose

        owner = self

        class VirtualTableChoose(MyChoose):
            def __init__(self, items: list[Any]) -> None:
                super().__init__(
                    items,
                    "Select Virtual Function",
                    [["Address", 12], ["Name", 24], ["Declaration", 48]],
                    13,
                )
                self.popup_names = ["Scan All", "-", "Scan", "-"]

            def OnInsertLine(self) -> None:  # noqa: N802 - IDA Choose API
                owner.scan_virtual_functions(model)

            def OnEditLine(self, n: int) -> None:  # noqa: N802 - IDA Choose API
                owner.scan_virtual_function(int(n), model)

            def OnGetIcon(self, n: int) -> int:  # noqa: N802 - IDA Choose API
                return 32 if owner.virtual_functions[n].visited else 160

        items = [
            [
                f"0x{int(vf.func_ea):X}",
                str(vf.name),
                str(vf.tinfo.dstr()) if getattr(vf, "tinfo", None) is not None and hasattr(vf.tinfo, "dstr") else "",
            ]
            for vf in self.virtual_functions
        ]
        chooser = VirtualTableChoose(items)
        index = chooser.Show(True)
        if index is None or int(index) < 0 or int(index) >= len(self.virtual_functions):
            return
        entry = self.virtual_functions[int(index)]
        entry.visited = True
        entry.show_location()

    @property
    def size(self) -> int:
        """A vtable member embedded in a class is one native pointer wide."""
        return 8 if idaapi.inf_is_64bit() else 4

    @property
    def type_name(self) -> str:
        return f"{self._local_type_name()} *"

    def _table_address(self) -> int:
        """Return the table EA, accepting the old dynamic ``func_ea`` field."""
        return int(self.address) or int(getattr(self, "func_ea", 0))

    def _local_type_name(self) -> str:
        ea = self._table_address()
        if ea:
            raw = idaapi.get_name(ea)
            raw_name = raw if isinstance(raw, str) else ""
            if raw_name and bool(idaapi.is_ident(raw_name)):
                if raw_name.startswith("off_"):
                    return "vtbl" + raw_name[3:]
                if "table" in raw_name.lower() or "vftable" in raw_name.lower():
                    return raw_name
                return "vtbl_" + raw_name
            try:
                demangled = idc.demangle_name(raw_name, idc.INF_SHORT_DN)
            except (AttributeError, RuntimeError):
                demangled = None
            if isinstance(demangled, str) and demangled:
                cleaned = demangled.replace("const ", "").replace("::_vftable", "_vtbl")
                cleaned = re.sub(r"[^0-9A-Za-z_:]", "_", cleaned).strip("_")
                if cleaned:
                    return cleaned.replace("::", "_")
            return f"vtable_{ea:X}"
        return f"vtable_{int(self.offset):X}"

    def _create_tinfo(self) -> Any:
        """Build a typed vtable UDT from the populated virtual functions."""
        if not self.virtual_functions:
            self.populate()
        if not self.virtual_functions:
            return None
        udt_data = idaapi.udt_type_data_t()
        ptr_size = 8 if idaapi.inf_is_64bit() else 4
        used_names: set[str] = set()
        for index, function in enumerate(self.virtual_functions):
            member = idaapi.udm_t()
            raw_name = str(function.name or f"fn_{int(function.offset):X}")
            name = re.sub(r"\W", "_", raw_name).strip("_") or f"fn_{int(function.offset):X}"
            if name in used_names:
                name = f"{name}_{index}"
            used_names.add(name)
            member.name = name
            member.offset = int(function.offset) * 8
            member.size = ptr_size * 8
            member_tinfo = getattr(function, "tinfo", None)
            try:
                if member_tinfo is not None and member_tinfo.is_func():
                    ptr_tinfo = idaapi.tinfo_t()
                    ptr_tinfo.create_ptr(member_tinfo)
                    member_tinfo = ptr_tinfo
            except (AttributeError, RuntimeError):
                member_tinfo = None
            if member_tinfo is None:
                member_tinfo = idaapi.tinfo_t()
                try:
                    void_tinfo = idaapi.tinfo_t(idaapi.BTF_VOID)
                    member_tinfo.create_ptr(void_tinfo)
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    return None
            member.type = member_tinfo
            udt_data.push_back(member)
        final_tinfo = idaapi.tinfo_t()
        if not final_tinfo.create_udt(udt_data, idaapi.BTF_STRUCT):
            return None
        return final_tinfo

    @staticmethod
    def check_address(ea: int) -> bool:
        """Return True if ``ea`` starts a named function-pointer table.

        This keeps the original plugin's important guards (the table itself
        must not be code and must have a name) without the original check's
        side effect of creating functions while merely populating a menu.
        """
        if ea <= 0 or int(ea) == int(idaapi.BADADDR):
            return False
        if is_code_ea(int(ea)) or not str(idaapi.get_name(int(ea))):
            return False

        ptr_size = 8 if idaapi.inf_is_64bit() else 4
        current = int(ea)
        valid = 0
        for _ in range(256):
            try:
                ptr = get_ptr(current)
            except (RuntimeError, TypeError, ValueError):
                break
            if ptr == 0:
                break
            if not (is_code_ea(ptr) or is_imported_ea(ptr, set())):
                break
            valid += 1
            current += ptr_size
        return valid > 0

    def import_to_structures(self, ask: bool = False) -> bool:
        """Register this vtable as a Local Type.

        Reads function pointers from ``self.address`` and preserves discovered
        virtual-function signatures when constructing the Local Type.

        Args:
            ask: If True, prompt the user with the generated C declaration
                for confirmation before registering.

        Returns:
            True if the type was successfully created, False otherwise.
        """
        from ..til.type_library import create_type

        # If the type was already imported by an earlier scan/pack, reuse it.
        vtable_name = self._local_type_name()
        existing = idaapi.tinfo_t()
        if existing.get_named_type(idaapi.get_idati(), vtable_name):
            return True

        final_tinfo = self._create_tinfo()
        if final_tinfo is None:
            logger.warning("No function pointers found for vtable %s", vtable_name)
            return False
        declaration = idaapi.print_tinfo(
            None,
            4,
            5,
            idaapi.PRTYPE_MULTI | idaapi.PRTYPE_TYPE | idaapi.PRTYPE_SEMI,
            final_tinfo,
            vtable_name,
            None,
        )
        if ask:
            shown = idaapi.ask_text(
                0x10000,
                declaration,
                "The following vtable type will be created:",
            )
            if not shown:
                return False
        if create_type(vtable_name, declaration):
            logger.info("Vtable %s added to Local Types", vtable_name)
            return True
        logger.error("Failed to create vtable %s", vtable_name)
        return False

    def get_udt_member(
        self, array_size: int = 0, offset: int = 0, flexible_array: bool = False
    ) -> Any:
        """Build the class member as a pointer to the imported vtable type."""
        if array_size or flexible_array:
            return None
        if not self.import_to_structures(ask=False):
            return None

        vtable_tinfo = idaapi.tinfo_t()
        if not vtable_tinfo.get_named_type(idaapi.get_idati(), self._local_type_name()):
            return None
        ptr_tinfo = idaapi.tinfo_t()
        if not ptr_tinfo.create_ptr(vtable_tinfo):
            return None

        udm = idaapi.udt_member_t()
        udm.name = self.name or "__vftable"
        udm.type = ptr_tinfo
        udm.offset = (int(self.offset) - int(offset)) * 8
        udm.size = self.size * 8
        return udm
