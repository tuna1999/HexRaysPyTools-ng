# Task 2.2 Brief: domain/types/func_type.py

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\types\func_type.py`
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\types\test_func_type.py`

## Required Content (verbatim)

### `src/hexrays_pytools/domain/types/func_type.py`

```python
"""Function type manipulation helpers.

Extracted from the original `core/helper.py`. Wraps `idaapi.func_type_data_t`
operations on function arguments, return type, and argument names.
"""
from __future__ import annotations
import idaapi  # type: ignore[import-not-found]


def get_func_argument_info(func_tinfo: idaapi.tinfo_t, arg_index: int) -> tuple[str, idaapi.tinfo_t]:  # type: ignore[name-defined]
    """Get (name, type) of the function argument at `arg_index`.

    Returns ("", empty tinfo) if the argument doesn't exist.
    """
    func_data = idaapi.func_type_data_t()
    if not func_tinfo.get_func_details(func_data):
        return "", idaapi.tinfo_t()
    if arg_index >= len(func_data):
        return "", idaapi.tinfo_t()
    arg = func_data[arg_index]
    return arg.name, arg.type


def set_func_argument(func_tinfo: idaapi.tinfo_t, arg_index: int, new_type: idaapi.tinfo_t) -> bool:  # type: ignore[name-defined]
    """Set the type of function argument at `arg_index` to `new_type`."""
    func_data = idaapi.func_type_data_t()
    if not func_tinfo.get_func_details(func_data):
        return False
    if arg_index >= len(func_data):
        return False
    func_data[arg_index].type = new_type
    return func_tinfo.create_func(func_data, idaapi.BT_FUNC)  # type: ignore[attr-defined]


def set_func_return(func_tinfo: idaapi.tinfo_t, new_type: idaapi.tinfo_t) -> bool:  # type: ignore[name-defined]
    """Set the return type of the function."""
    func_data = idaapi.func_type_data_t()
    if not func_tinfo.get_func_details(func_data):
        return False
    func_data.rettype = new_type
    return func_tinfo.create_func(func_data, idaapi.BT_FUNC)  # type: ignore[attr-defined]
```

### `tests/domain/types/test_func_type.py`

```python
"""Test func_type."""
from hexrays_pytools.domain.types.func_type import get_func_argument_info, set_func_argument, set_func_return


def test_get_func_argument_info_returns_name_and_type() -> None:
    """get_func_argument_info returns (name, type) for valid arg_index."""
    idaapi = __import__("idaapi")
    func_tinfo = MagicMock()
    arg = MagicMock()
    arg.name = "size"
    arg.type = MagicMock()
    func_data = MagicMock()
    func_data.__len__.return_value = 2
    func_data.__getitem__.return_value = arg
    func_tinfo.get_func_details.return_value = True
    idaapi.func_type_data_t.return_value = func_data

    name, arg_type = get_func_argument_info(func_tinfo, 0)
    assert name == "size"


def test_set_func_argument_modifies_type() -> None:
    """set_func_argument changes the type of the argument at arg_index."""
    idaapi = __import__("idaapi")
    func_tinfo = MagicMock()
    func_data = MagicMock()
    func_data.__len__.return_value = 1
    func_data.__getitem__.return_value = MagicMock()
    func_tinfo.get_func_details.return_value = True
    func_tinfo.create_func.return_value = True
    idaapi.func_type_data_t.return_value = func_data

    new_type = MagicMock()
    assert set_func_argument(func_tinfo, 0, new_type) is True
    func_tinfo.create_func.assert_called_once()


def test_set_func_return_modifies_rettype() -> None:
    """set_func_return changes the return type."""
    idaapi = __import__("idaapi")
    func_tinfo = MagicMock()
    func_data = MagicMock()
    func_tinfo.get_func_details.return_value = True
    func_tinfo.create_func.return_value = True
    idaapi.func_type_data_t.return_value = func_data

    new_type = MagicMock()
    assert set_func_return(func_tinfo, new_type) is True
    assert func_data.rettype is new_type
```

Add the MagicMock import:

```python
from unittest.mock import MagicMock
```

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/types/test_func_type.py -v
python -m mypy --strict src/hexrays_pytools/domain/types/func_type.py
python -m ruff check src/hexrays_pytools/domain/types/func_type.py tests/domain/types/test_func_type.py
```

## Commit

```bash
git add src/hexrays_pytools/domain/types/func_type.py tests/domain/types/test_func_type.py
git commit -m "feat(types): add func_type (get/set func arg, return)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.2-report.md`

Apply minimal lint fixes. Document deviations in DONE_WITH_CONCERNS.