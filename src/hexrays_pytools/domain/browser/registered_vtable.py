"""RegisteredVTable — a vtable that exists in Local Types (not discovered).

Renamed from `core/classes.VirtualTable` to disambiguate from
`recon.DiscoveredVTable` (the working-copy vtable from scanning).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VirtualMethod:
    """A single method in a registered vtable."""
    name: str
    tinfo: Any = None
    address: int = 0
    parents: list[Any] = field(default_factory=list)  # parent vtable ordinals (for multi-inheritance)


@dataclass
class RegisteredVTable:
    """A vtable that lives in Local Types."""
    name: str
    ordinal: int = 0
    class_name: str = ""
    offset: int = 0
    virtual_functions: list[Any] = field(default_factory=list)  # list[VirtualMethod]
    tinfo: Any = None

    def tooltip(self) -> str:
        """Return a hover hint for the vtable."""
        if self.tinfo is not None and hasattr(self.tinfo, "dstr"):
            return str(self.tinfo.dstr())
        return f"{self.class_name}::{self.name}@+0x{self.offset:x}"
