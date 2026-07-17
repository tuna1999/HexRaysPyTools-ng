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
import idc  # type: ignore[import-not-found]

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

    virtual_functions: list[Any] = field(default_factory=list)

    @staticmethod
    def check_address(ea: int) -> bool:
        """Return True if `ea` looks like a vtable (heuristic).

        Stub for the rewrite — a real vtable would need to read the data
        at ``ea`` and verify each entry is a function pointer. The original
        plugin used a more sophisticated check (struct at ea must be a
        function-pointer array). For now, any non-zero address is considered
        a candidate — the action gates on this AND the user explicitly
        invoking the action at that address.
        """
        return ea > 0

    def import_to_structures(self, ask: bool = False) -> bool:
        """Register this vtable as a Local Type.

        Reads ``len(self.virtual_functions)`` function pointers from
        ``self.func_ea`` (or ``self.ea`` as fallback), builds a UDT with one
        ``void*`` field per pointer, and registers it as
        ``vtable_<hex_offset>``.

        Args:
            ask: If True, prompt the user with the generated C declaration
                for confirmation before registering.

        Returns:
            True if the type was successfully created, False otherwise.
        """
        from ..til.type_library import create_type

        # Read function pointers (best-effort; gaps handled).
        entries: list[str] = []
        ea = int(getattr(self, "func_ea", 0)) or int(getattr(self, "ea", 0))
        # Void pointer — matches the original's `void*` field type.
        ptr_size = 8 if idaapi.inf_is_64bit() else 4
        # Discover the vtable length — read while ea is a code pointer.
        current_ea = ea
        max_entries = 256  # safety bound
        while len(entries) < max_entries:
            try:
                ptr = int(idc.get_wide_dword(current_ea))
            except Exception:  # noqa: BLE001 — defensive
                break
            if ptr == 0 or not idaapi.is_code(idaapi.get_full_flags(ptr & ~1)):
                break
            # Name the field by its offset (matches the original
            # VirtualTable.get_udt_member naming convention).
            offset_hex = current_ea - ea
            entries.append(f"  void* fn_{offset_hex:X};")
            current_ea += ptr_size

        if not entries:
            logger.warning("No function pointers found at 0x%X — nothing to import", ea)
            return False

        vtable_name = f"vtable_{int(self.offset):X}"
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
