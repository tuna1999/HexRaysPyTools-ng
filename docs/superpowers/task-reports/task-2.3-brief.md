# Task 2.3 Brief: domain/types/udt_builder.py

## Files

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\types\udt_builder.py`
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\types\test_udt_builder.py`

## Content (verbatim)

### `src/hexrays_pytools/domain/types/udt_builder.py`

```python
"""UDT (struct/union) builder from member list.

Pure-ish: takes a list of (name, offset, size, tinfo) tuples and returns
a udt_type_data_t ready to be applied to a Local Type.

Extracted from the original `core/temporary_structure.py:pack()` method.
"""
from __future__ import annotations
import idaapi  # type: ignore[import-not-found]


def create_padding_udt_member(offset: int, size: int) -> idaapi.udt_member_t:  # type: ignore[name-defined]
    """Create a gap_<offset> padding udt_member."""
    member = idaapi.udt_member_t()
    member.name = f"gap_{offset:X}"
    member.offset = offset
    # Padding type: byte array of `size` bytes
    pad_type = idaapi.tinfo_t()
    pad_type.create_array(idaapi.tinfo_t(idaapi.BT_BYTE), size)  # type: ignore[attr-defined]
    member.type = pad_type
    member.size = size
    return member
```

### `tests/domain/types/test_udt_builder.py`

```python
"""Test udt_builder."""
from hexrays_pytools.domain.types.udt_builder import create_padding_udt_member


def test_create_padding_member_name() -> None:
    """Padding member name follows gap_<offset_in_hex> convention."""
    idaapi = __import__("idaapi")
    member = MagicMock()
    idaapi.udt_member_t.return_value = member
    idaapi.tinfo_t.return_value = MagicMock()

    result = create_padding_udt_member(0x10, 4)
    assert member.name == "gap_10"


def test_create_padding_member_offset() -> None:
    """Padding member offset matches input."""
    idaapi = __import__("idaapi")
    member = MagicMock()
    idaapi.udt_member_t.return_value = member
    idaapi.tinfo_t.return_value = MagicMock()

    create_padding_udt_member(0x20, 8)
    assert member.offset == 0x20


def test_create_padding_member_size() -> None:
    """Padding member size matches input."""
    idaapi = __import__("idaapi")
    member = MagicMock()
    idaapi.udt_member_t.return_value = member
    idaapi.tinfo_t.return_value = MagicMock()

    create_padding_udt_member(0x0, 16)
    assert member.size == 16
```

Add `from unittest.mock import MagicMock` to the import.

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/types/test_udt_builder.py -v
python -m mypy --strict src/hexrays_pytools/domain/types/udt_builder.py
python -m ruff check src/hexrays_pytools/domain/types/udt_builder.py tests/domain/types/test_udt_builder.py
```

## Commit

```bash
git add src/hexrays_pytools/domain/types/udt_builder.py tests/domain/types/test_udt_builder.py
git commit -m "feat(types): add udt_builder (create_padding_udt_member)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.3-report.md`