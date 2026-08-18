"""Discovered vtable — found during struct reconstruction.

Renamed from `core/temporary_structure.VirtualTable` to avoid collision
with `core/classes.VirtualTable` (a different concept: a registered vtable
in Local Types).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import idaapi  # type: ignore[import-not-found]

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


@dataclass
class ImportedVirtualFunction:
    """Virtual function imported from a type library (no decompile)."""

    offset: int
    tinfo: Any = None
    name: str = ""


@dataclass
class DiscoveredVTable(AbstractMember):
    """A vtable discovered while scanning a struct.

    A working copy — different from the registered vtable in Local Types
    (see `domain/browser/registered_vtable.py`).
    """

    address: int = 0
    virtual_functions: list[Any] = field(default_factory=list)

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
            return f"vtable_{ea:X}"
        return f"vtable_{int(self.offset):X}"

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

        Reads function pointers from ``self.address`` (or the legacy dynamic
        ``self.func_ea`` field), builds a UDT with one
        ``void*`` field per pointer, and registers it as
        ``vtable_<hex_offset>``.

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

        # Read function pointers (best-effort; gaps handled).
        entries: list[str] = []
        ea = self._table_address()
        if not ea:
            logger.warning("Vtable has no table address — nothing to import")
            return False
        ptr_size = 8 if idaapi.inf_is_64bit() else 4
        # Discover the vtable length — read while ea is a code pointer.
        current_ea = ea
        max_entries = 256  # safety bound
        while len(entries) < max_entries:
            try:
                ptr = get_ptr(current_ea)
            except (RuntimeError, TypeError, ValueError):
                break
            if ptr == 0 or not (is_code_ea(ptr) or is_imported_ea(ptr, set())):
                break
            # Name the field by its offset (matches the original
            # VirtualTable.get_udt_member naming convention).
            offset_hex = current_ea - ea
            entries.append(f"  void* fn_{offset_hex:X};")
            current_ea += ptr_size

        if not entries:
            logger.warning("No function pointers found at 0x%X — nothing to import", ea)
            return False

        declaration = f"struct {vtable_name} {{\n" + "\n".join(entries) + "\n};"
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

    def get_udt_member(self, array_size: int = 0, offset: int = 0) -> Any:
        """Build the class member as a pointer to the imported vtable type."""
        if array_size:
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
