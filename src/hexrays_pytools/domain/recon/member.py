"""Struct member candidate data classes.

Extracted from `core/temporary_structure.py` (AbstractMember, Member, VoidMember).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AbstractMember:
    """Base class for a struct member candidate."""
    offset: int
    tinfo: Any = None
    name: str = ""
    origin: int = 0
    enabled: bool = True
    is_array: bool = False
    array_size: int = 1
    scanned_variables: set[int] = field(default_factory=set)

    @property
    def size(self) -> int:
        if self.tinfo is None:
            return 0
        try:
            return int(self.tinfo.get_size())
        except (AttributeError, RuntimeError):
            return 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AbstractMember):
            return NotImplemented
        # Merge scanned_variables on match (original plugin behavior)
        if self.offset == other.offset and self.size == other.size:
            self.scanned_variables |= other.scanned_variables
            return True
        return False

    def __hash__(self) -> int:
        return hash((self.offset, self.size))

    def __lt__(self, other: AbstractMember) -> bool:
        return self.offset < other.offset


@dataclass
class Member(AbstractMember):
    """A struct member with a known tinfo."""
    pass


@dataclass
class VoidMember(AbstractMember):
    """Fallback member when no tinfo can be inferred (byte/char)."""
    tinfo: Any = None
    name: str = "void"

    def type_equals_to(self, other_type: Any) -> bool:
        return True  # wildcard — always matches
