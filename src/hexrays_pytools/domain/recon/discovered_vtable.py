"""Discovered vtable — found during struct reconstruction.

Renamed from `core/temporary_structure.VirtualTable` to avoid collision
with `core/classes.VirtualTable` (a different concept: a registered vtable
in Local Types).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .member import AbstractMember


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
        """Return True if `ea` looks like a vtable (heuristic)."""
        # Stub: real impl requires reading struct at ea
        return ea > 0
