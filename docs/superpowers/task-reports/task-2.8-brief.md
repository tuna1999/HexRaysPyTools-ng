# Task 2.8 Brief: domain/recon/member.py

## Files (3)
1. `src/hexrays_pytools/domain/recon/member.py`
2. `tests/domain/recon/test_member.py`

## `member.py` (verbatim)

```python
"""Struct member candidate data classes.

Extracted from `core/temporary_structure.py` (AbstractMember, Member, VoidMember).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

import idaapi  # type: ignore[import-not-found]


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
    scanned_variables: set = field(default_factory=set)

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

    def __lt__(self, other: "AbstractMember") -> bool:
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
```

## `test_member.py` (verbatim)

```python
"""Test AbstractMember / Member / VoidMember."""
from hexrays_pytools.domain.recon.member import AbstractMember, Member, VoidMember


def test_abstract_member_default_fields() -> None:
    """AbstractMember has sensible defaults."""
    m = AbstractMember(offset=0x10)
    assert m.tinfo is None
    assert m.name == ""
    assert m.enabled is True
    assert m.size == 0


def test_abstract_member_size_from_tinfo() -> None:
    """size property reads from tinfo.get_size()."""
    m = AbstractMember(offset=0)
    tinfo = MagicMock()
    tinfo.get_size.return_value = 4
    m.tinfo = tinfo
    assert m.size == 4


def test_member_eq_merges_scanned_variables() -> None:
    """Two AbstractMembers with same offset+size are equal and merge scanned_variables."""
    a = AbstractMember(offset=0x10)
    a.scanned_variables = {1, 2}
    b = AbstractMember(offset=0x10)
    b.scanned_variables = {3}
    assert a == b
    assert a.scanned_variables == {1, 2, 3}


def test_member_lt_compares_offset() -> None:
    """AbstractMember orders by offset."""
    a = AbstractMember(offset=0x10)
    b = AbstractMember(offset=0x20)
    assert a < b


def test_void_member_wildcard_type_match() -> None:
    """VoidMember.type_equals_to always returns True."""
    v = VoidMember(offset=0)
    assert v.type_equals_to("anything") is True


def test_member_class_is_subclass() -> None:
    """Member is a subclass of AbstractMember."""
    m = Member(offset=0, name="x")
    assert isinstance(m, AbstractMember)
    assert m.name == "x"
```

Add `from unittest.mock import MagicMock` to imports.

## Verification
```bash
PYTHONPATH=src pytest tests/domain/recon/test_member.py -v
python -m mypy --strict src/hexrays_pytools/domain/recon/member.py
python -m ruff check src/hexrays_pytools/domain/recon/member.py tests/domain/recon/test_member.py
```

## Commit
```bash
git add src/hexrays_pytools/domain/recon/member.py tests/domain/recon/test_member.py
git commit -m "feat(recon): add AbstractMember/Member/VoidMember data classes"
```

## Report
`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.8-report.md`