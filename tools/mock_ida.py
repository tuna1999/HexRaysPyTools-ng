"""Install mock IDA Python modules into sys.modules for unit tests.

This module is the test infrastructure for running pytest WITHOUT a real IDA
installation. It provides:

- A `_MockIdaModule` class that returns MagicMock for any attribute access
  (similar to the original `HexRaysPyTools` plugin's `idaapi` global, which is
  a SWIG module).

- `install()` registers all IDA-related modules as mocks. Idempotent.

- `reset()` clears call history between tests.

Usage:
    # In tests/conftest.py or test files:
    from tools.mock_ida import install, reset
    install()
    # Now you can `import idaapi; idaapi.tinfo_t()` etc.
"""
from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock

# Modules that should be mocked
MOCK_MODULES: tuple[str, ...] = (
    "idaapi", "idc", "idautils", "ida_hexrays", "ida_typeinf",
    "ida_name", "ida_kernwin", "ida_idaapi", "ida_settings",
    "ida_funcs", "ida_lines", "ida_nalt", "ida_diskio", "ida_idp",
    "ida_widget", "ida_graph", "ida_gdl", "ida_netnode",
    "PySide6", "PySide6.QtCore", "PySide6.QtWidgets", "PySide6.QtGui",
    "PyQt5", "PyQt5.QtCore", "PyQt5.QtWidgets", "PyQt5.QtGui",
)


class _MockIdaModule:
    """Catch-all mock: any attribute returns a MagicMock.

    Pre-creates some common constants (BADADDR, BADSIZE, etc.) to avoid
    `MagicMock() == 0xFFFFFFFFFFFFFFFF` confusion in tests.
    """
    # Common IDA constants
    BADADDR: int = 0xFFFFFFFFFFFFFFFF
    BADSIZE: int = 0xFFFFFFFFFFFFFFFF
    BADORD: int = 0xFFFFFFFFFFFFFFFF
    PT_TYP: int = 1
    NTF_REPLACE: int = 0x00000002
    NTF_NOBASE: int = 0x00000000
    BTF_STRUCT: int = 0x00000004
    BTF_UNION: int = 0x00000005
    BTF_ENUM: int = 0x00000006
    BTF_CHAR: int = 0x00000010
    BTF_BYTE: int = 0x00000000
    BT_VOID: int = 0x00000001
    BT_INT: int = 0x00000003
    BTM_CONST: int = 0x00000004
    SEGPERM_EXEC: int = 0x00000004
    TINFO_DEFINITE: int = 0x00000010
    CM_CC_MASK: int = 0x0000000F
    CM_CC_CDECL: int = 0x00000000
    CM_CC_STDCALL: int = 0x00000001
    CM_CC_FASTCALL: int = 0x00000003
    CM_CC_THISCALL: int = 0x00000002
    CM_CC_ELLIPSIS: int = 0x00000004
    CM_CC_SPECIAL: int = 0x0000000B
    CM_CC_UNKNOWN: int = 0x00000000
    PRTYPE_MULTI: int = 0x00000001
    PRTYPE_TYPE: int = 0x00000002
    PRTYPE_SEMI: int = 0x00000004
    AST_ENABLE_ALWAYS: int = 0x00000004
    AST_ENABLE_FOR_WIDGET: int = 0x00000003
    AST_ENABLE: int = 0x00000001
    AST_DISABLE: int = 0x00000000
    AST_DISABLE_FOR_WIDGET: int = 0x00000002
    BWN_PSEUDOCODE: int = 0x00000000
    BWN_TILIST: int = 0x00000001
    BWN_DISASM: int = 0x00000002
    BWN_FUNCS: int = 0x00000003
    BWN_LOCTYPS: int = 0x00000004
    VDI_EXPR: int = 0x00000000
    VDI_FUNC: int = 0x00000001
    VDI_LVAR: int = 0x00000002
    cot_var: int = 0x00000001
    cot_obj: int = 0x00000002
    cot_memptr: int = 0x00000003
    cot_memref: int = 0x00000004
    cot_num: int = 0x00000005
    cot_call: int = 0x00000006
    cot_asg: int = 0x00000007
    cot_cast: int = 0x00000008
    cot_ref: int = 0x00000009
    cot_add: int = 0x0000000A
    cot_sub: int = 0x0000000B
    cot_idx: int = 0x0000000C
    cot_helper: int = 0x0000000D
    cot_fnum: int = 0x0000000E
    cot_fadd: int = 0x0000000F
    cot_fsub: int = 0x00000010
    cot_fmul: int = 0x00000011
    cot_fdiv: int = 0x00000012
    cit_if: int = 0x00000020
    cit_return: int = 0x00000021
    cit_block: int = 0x00000022
    cit_goto: int = 0x00000023
    CMAT_BUILT: int = 0x00000000
    CMAT_TRANS1: int = 0x00000001
    CMAT_TRANS2: int = 0x00000002
    CMAT_FINAL: int = 0x00000003
    hxe_populating_popup: int = 0x00000001
    hxe_double_click: int = 0x00000002
    hxe_maturity: int = 0x00000003
    CV_POST: int = 0x00000001
    DELIT_SIMPLE: int = 0x00000000
    STRMEM_OFFSET: int = 0x00000000
    AR_STR: int = 0x00000005
    INF_SHORT_DN: int = 0x00000003
    INF_LONG_DN: int = 0x00000002

    def __getattr__(self, name: str) -> Any:
        # Names starting with "_" are real attributes (Python internals, the
        # constants above). Anything else is a mock. Cache in __dict__ so
        # repeated access returns the SAME MagicMock instance — this is what
        # tests rely on (e.g. `idaapi.is_code.return_value = True` followed by
        # a later `idaapi.is_code(...)` call must see the configured value), and
        # what `reset()` needs (it iterates attributes expecting stability).
        if name.startswith("_"):
            raise AttributeError(name)
        mock = MagicMock(name=f"ida.{self.__class__.__name__}.{name}")
        self.__dict__[name] = mock
        return mock


def install() -> None:
    """Install all mock IDA modules into sys.modules. Idempotent."""
    for mod_name in MOCK_MODULES:
        if mod_name not in sys.modules:
            # mypy: sys.modules is typed as dict[str, Module]; a MagicMock-backed
            # catch-all is intentional here. The mismatch is a known mypy limitation.
            sys.modules[mod_name] = _MockIdaModule()  # type: ignore[assignment]


def reset() -> None:
    """Reset call history on all mock modules (between tests)."""
    for mod_name in MOCK_MODULES:
        mod = sys.modules.get(mod_name)
        if mod is None:
            continue
        for attr_name in dir(mod):
            if attr_name.startswith("_"):
                continue
            attr = getattr(mod, attr_name, None)
            if isinstance(attr, MagicMock):
                attr.reset_mock()
