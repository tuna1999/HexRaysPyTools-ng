# Task 1.1 Brief: infra/arch/arch.py

## Where This Fits

Phase 1, Task 1.1. First task of infrastructure layer. Provides architecture abstraction (ARM thumb bit, x86/x64 pointer reading) — pure thin wrapper around IDA API that is mockable.

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\infra\__init__.py` (empty)
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\infra\arch\__init__.py` (empty)
3. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\infra\arch\arch.py`
4. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\infra\__init__.py` (empty)
5. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\infra\test_arch.py`

## Required Content (verbatim)

### `src/hexrays_pytools/infra/arch/arch.py`

```python
"""Architecture abstraction: ARM thumb bit, x86/x64 pointer reading.

Replaces helper.py's `is_code_ea` and `get_ptr` from the original plugin.
Centralizes architecture-specific code so other modules don't deal with
ARM thumb bit masking or 32/64-bit pointer widths.
"""
from __future__ import annotations
import idaapi


def is_code_ea(ea: int) -> bool:
    """Check if `ea` points to code, handling ARM thumb bit (mask 1)."""
    return idaapi.is_code(idaapi.get_full_flags(ea & ~1))


def get_ptr(ea: int) -> int:
    """Read a pointer (4 or 8 bytes) at `ea`, stripping ARM thumb bit."""
    flags = idaapi.get_full_flags(ea & ~1)
    if idaapi.get_64bit():
        return idaapi.get_qword(ea & ~1) if idaapi.is_data(flags) else idaapi.get_wide_dword(ea & ~1)
    return idaapi.get_wide_dword(ea & ~1)
```

### `tests/infra/test_arch.py`

```python
"""Test arch.is_code_ea and arch.get_ptr."""
from unittest.mock import MagicMock
from hexrays_pytools.infra.arch.arch import is_code_ea, get_ptr


def test_is_code_ea_strips_arm_thumb_bit() -> None:
    """is_code_ea(0x1001) should mask off the thumb bit before checking."""
    is_code_ea(0x1001)
    idaapi = __import__("idaapi")
    # The mock records the call to get_full_flags with the masked address
    call_args = idaapi.get_full_flags.call_args
    assert call_args[0][0] == 0x1000  # 0x1001 & ~1


def test_is_code_ea_returns_bool() -> None:
    """is_code_ea returns the result of idaapi.is_code()."""
    __import__("idaapi").is_code.return_value = True
    assert is_code_ea(0x1000) is True


def test_get_ptr_x86_uses_wide_dword() -> None:
    """get_ptr on 32-bit IDA reads a wide dword."""
    __import__("idaapi").get_64bit.return_value = False
    get_ptr(0x2000)
    __import__("idaapi").get_wide_dword.assert_called()


def test_get_ptr_x64_uses_qword() -> None:
    """get_ptr on 64-bit IDA reads a qword for data, dword for code."""
    idaapi = __import__("idaapi")
    idaapi.get_64bit.return_value = True
    idaapi.is_data.return_value = True
    get_ptr(0x2000)
    idaapi.get_qword.assert_called()
```

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/infra/test_arch.py -v
# RED first (ModuleNotFoundError), then GREEN (4 tests pass)
python -m mypy --strict src/hexrays_pytools/infra/arch/arch.py
python -m ruff check src/hexrays_pytools/infra/ tests/infra/
```

## Commit

```bash
git add src/hexrays_pytools/infra/ tests/infra/
git commit -m "feat(infra): add arch.is_code_ea and arch.get_ptr (ARM thumb)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-1.1-report.md`

## Note

The tests use the mock_ida infrastructure from Phase 0 (Task 0.8). The mock `idaapi.is_code`, `get_full_flags`, etc. are MagicMock instances that return MagicMock by default. Tests set `.return_value` where needed. The `__import__("idaapi")` pattern is used because the module is installed via the conftest mock — `import idaapi` at top of test would also work but `__import__` allows assertion access to the mock object directly.

If brief has lint issues (e.g., the `__import__` pattern), apply minimal fixes and document in DONE_WITH_CONCERNS.

## Self-Review checklist
- Files exactly as brief?
- 4 tests pass?
- mypy --strict clean?
- ruff clean?
- Single commit, exact message?
