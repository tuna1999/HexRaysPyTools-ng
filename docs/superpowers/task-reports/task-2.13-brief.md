# Task 2.13 Brief: domain/til/type_library.py

## Context

Replaces `core/type_library.py` (72 LOC). The original used `ctypes.windll["ida64.dll"]` to call `enable_numbered_types` directly (B2 bug — FFI bypass, `linux2` dead code). The rewrite uses `idaapi.enable_numbered_types` if available, with graceful fallback.

## Files

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\til\__init__.py` (empty)
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\til\type_library.py`
3. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\til\__init__.py` (empty)
4. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\til\test_type_library.py`

## Content (verbatim)

### `src/hexrays_pytools/domain/til/type_library.py`

```python
"""Type library (TIL) operations.

Replaces `core/type_library.py`. The original used ctypes FFI to call
`enable_numbered_types` directly, with `linux2` (Py2-only) as a
fallback platform check. The rewrite uses `idaapi.enable_numbered_types`
if the IDA 9.x SDK exposes it; otherwise logs a warning and skips the
numbering (graceful degradation).
"""
from __future__ import annotations
import logging

import idaapi  # type: ignore[import-not-found]
import idc  # type: ignore[import-not-found]

from ...ui.chooser import MyChoose

logger = logging.getLogger(__name__)


def choose_til() -> tuple | None:
    """Prompt the user to pick a TIL from the loaded libraries.

    Returns (til_t, max_ordinal, is_local) or None if user cancels.
    """
    idati = idaapi.get_idati()
    libs = [(idati, idati.name, idati.desc)]
    for idx in range(idati.nbases):
        lib = idati.base(idx)
        libs.append((lib, lib.name, lib.desc))

    chooser = MyChoose(
        [[x[1], x[2]] for x in libs],
        "Select Library",
        [["Library", 10 | idaapi.Choose.CHCOL_PLAIN], ["Description", 30 | idaapi.Choose.CHCOL_PLAIN]],
        69,
    )
    pick = chooser.Show(True)
    if pick == -1:
        return None
    selected = libs[pick][0]
    max_ord = idaapi.get_ordinal_count(selected)
    if max_ord == idaapi.BADORD:
        # Try to enable numbered types via the official API; if missing, log and skip.
        enable = getattr(idaapi, "enable_numbered_types", None)
        if enable is None:
            logger.warning("idaapi.enable_numbered_types not available in this IDA version; skipping")
            return selected, 0, pick == 0
        enable(selected, True)
        max_ord = idaapi.get_ordinal_count(selected)
    return selected, int(max_ord), pick == 0


def create_type(name: str, declaration: str) -> bool:
    """Parse a C declaration and add it as a named type. Returns True on success."""
    tif = idaapi.tinfo_t()
    if tif.get_named_type(idaapi.get_idati(), name):
        logger.error("Type with name '%s' already exists", name)
        return False
    idaapi.idc_parse_types(declaration, 0)
    if not tif.get_named_type(idaapi.get_idati(), name):
        logger.error("Failed to create type '%s'", name)
        return False
    return True


def import_type(library, name: str) -> int | None:
    """Import a named type from `library`. Returns new ordinal or None on failure."""
    last_ordinal = int(idaapi.get_ordinal_count(idaapi.get_idati()))
    type_id = idc.import_type(library, -1, name)
    if type_id == idaapi.BADORD:
        return None
    return last_ordinal
```

### `tests/domain/til/test_type_library.py`

```python
"""Test type_library."""
from hexrays_pytools.domain.til.type_library import create_type, import_type, choose_til, OLD_ARRAY_NAME
```

Note: OLD_ARRAY_NAME was removed (it was in xref_storage, not here). Brief is for type_library. Adjust to import what's actually defined.

## Content (corrected)

```python
"""Test type_library."""
from hexrays_pytools.domain.til.type_library import create_type, import_type, choose_til


def test_create_type_succeeds_for_new_type() -> None:
    """create_type returns True for a new type name."""
    idaapi = __import__("idaapi")
    tif = MagicMock()
    idaapi.tinfo_t.return_value = tif
    # First call (existence check) returns False (not exists)
    # Second call (verify) returns True
    tif.get_named_type.side_effect = [False, True]
    assert create_type("MyStruct", "struct MyStruct { int x; };") is True


def test_create_type_fails_if_already_exists() -> None:
    """create_type returns False if name already exists."""
    idaapi = __import__("idaapi")
    tif = MagicMock()
    idaapi.tinfo_t.return_value = tif
    tif.get_named_type.return_value = True  # name already exists
    assert create_type("Existing", "struct Existing { int x; };") is False


def test_import_type_returns_ordinal_on_success() -> None:
    """import_type returns the new ordinal on success."""
    idaapi = __import__("idaapi")
    idc = __import__("idc")
    idaapi.get_ordinal_count.return_value = 42
    idc.import_type.return_value = 5  # not BADORD
    assert import_type(MagicMock(), "MyType") == 42


def test_import_type_returns_none_on_failure() -> None:
    """import_type returns None if idc.import_type returns BADORD."""
    idaapi = __import__("idaapi")
    idc = __import__("idc")
    idaapi.BADORD = -1
    idc.import_type.return_value = -1
    assert import_type(MagicMock(), "MissingType") is None


def test_choose_til_returns_none_on_cancel() -> None:
    """choose_til returns None when user cancels the chooser."""
    # Set up the chooser to return -1
    import hexrays_pytools.ui.chooser as chooser_mod
    from unittest.mock import patch
    with patch.object(chooser_mod, "MyChoose") as MockChoose:
        instance = MagicMock()
        instance.Show.return_value = -1
        MockChoose.return_value = instance
        assert choose_til() is None
```

Add `from unittest.mock import MagicMock, patch` to imports.

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/til/test_type_library.py -v
python -m mypy --strict src/hexrays_pytools/domain/til/type_library.py
python -m ruff check src/hexrays_pytools/domain/til/ tests/domain/til/
```

## Commit

```bash
git add src/hexrays_pytools/domain/til/ tests/domain/til/
git commit -m "feat(til): add type_library (no ctypes FFI; graceful fallback for IDA 9.x)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.13-report.md`

Note: brief mentions `MyChoose` from `ui.chooser` which doesn't exist yet (planned for Task 3.5). Create a stub at `src/hexrays_pytools/ui/__init__.py` (empty) and `src/hexrays_pytools/ui/chooser.py` with the `MyChoose` class definition.