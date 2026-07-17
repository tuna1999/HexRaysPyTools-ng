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
    CM_CC_SPECIALP: int = 0x0000000C
    CM_CC_SPECIALE: int = 0x0000000D
    CM_CC_PASCAL: int = 0x00000005
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

    # SWIG base types that production code subclasses (e.g. plugin_t,
    # action_handler_t). These MUST be real classes, not MagicMocks — a
    # MagicMock base makes the subclass itself a MagicMock instance, so
    # `class MyPlugin(idaapi.plugin_t)` would silently produce a mock instead
    # of a real class. Provide a plain base so subclassing works in tests and
    # in the bare `python -c` import verification.
    class plugin_t:  # noqa: N801 - keep IDA SWIG casing
        pass

    class action_handler_t:  # noqa: N801 - keep IDA SWIG casing
        pass

    class action_t:  # noqa: N801 - keep IDA SWIG casing
        pass

    class ctree_parentee_t:  # noqa: N801 - keep IDA SWIG casing
        """Stand-in for ``idaapi.ctree_parentee_t``.

        Production subclasses (the Object*Visitor hierarchy in
        domain/scanner/) read/assign ``cv_flags``, read ``parents``, and
        call ``apply_to(body, parent)``. Provide these as instance state so
        ``cv_flags |= CV_POST`` and ``self.parents`` work under mock_ida.
        Tests that need a controllable ``parents`` stack or want to assert
        on ``apply_to`` just set the attribute directly.
        """
        def __init__(self) -> None:
            self.cv_flags: int = 0
            self.parents: list[Any] = []

        def apply_to(self, body: Any, parent: Any) -> None:
            """No-op traversal stub — real dispatch only happens in IDA."""


    class ctree_item_t:  # noqa: N801 - keep IDA SWIG casing
        """Stand-in for ``idaapi.ctree_item_t``.

        Production code does ``isinstance(arg, idaapi.ctree_item_t)`` to
        dispatch between cexpr-shaped and item-shaped inputs in factory
        functions (e.g. ``ScanObject.create``). A MagicMock base would
        raise ``TypeError: isinstance() arg 2 must be a type`` — must be a
        real class.

        Attributes (``citype``, ``e``) are class-level defaults so tests
        can use ``MagicMock(spec=idaapi.ctree_item_t)`` (which enforces
        ``spec``-only attribute access) and still configure these three
        fields without raising ``AttributeError``.
        """
        citype: int = 0  # one of idaapi.VDI_*
        e: Any = None

        def get_lvar(self) -> Any:
            """Returns the local var attached to this item, or None."""
            return None

    class cexpr_t:  # noqa: N801 - keep IDA SWIG casing
        """Stand-in for ``idaapi.cexpr_t``. Subclassed by visitors."""
        op: int = 0

    class carg_t:  # noqa: N801 - keep IDA SWIG casing
        """Stand-in for ``idaapi.carg_t``."""
        op: int = 0

    class lvar_t:  # noqa: N801 - keep IDA SWIG casing
        """Stand-in for ``idaapi.lvar_t``."""
        name: str = ""
        def type(self) -> Any: ...
        cmt: str = ""

    class DecompilationFailure(Exception):  # noqa: N818 - mirror IDA SWIG casing
        """Stand-in for ``idaapi.DecompilationFailure``.

        Production code (``scanner/helpers.decompile_function``) catches this
        when Hex-Rays cannot decompile a function. It MUST be a real
        Exception subclass — a MagicMock would not be raisable, so
        ``except idaapi.DecompilationFailure`` in production code and
        ``side_effect=idaapi.DecompilationFailure`` in tests would both
        misbehave.
        """

    # UI base types that production code subclasses (PluginForm for dock
    # forms, GraphViewer for graph widgets, Choose for list choosers). Same
    # rationale as plugin_t above: a MagicMock base would make
    # `class StructureBuilder(idaapi.PluginForm)` produce a mock instance
    # whose __init__ never runs, so attribute assertions in widget tests fail.
    # Provide real bases so subclassing + __init__ work under mock_ida.
    class PluginForm:  # noqa: N801 - keep IDA SWIG casing
        """Stand-in for idaapi.PluginForm.

        The real PluginForm exposes several ``staticmethod`` form-to-widget
        converters. IDA 9.4's ``FormToPySideWidget`` is broken (it calls the
        nonexistent ``ctx.QtGui.QWidget.FromCapsule``), so production code
        routes through ``TWidgetToQtPythonWidget`` instead. Declaring these
        two as named attributes here (rather than leaving the class empty)
        means ``monkeypatch.setattr(idaapi.PluginForm, ...)`` does not raise
        ``AttributeError ... has no attribute`` — pytest's default
        ``raising=True`` would otherwise reject patches against names absent
        from the mock class. The no-op defaults are never reached in tests
        that patch them.
        """

        @staticmethod
        def TWidgetToQtPythonWidget(tw: Any, ctx: Any = None) -> Any:  # noqa: N802 - IDA SWIG casing
            """No-op default; tests patch this to return a fake widget."""

        # Alias mirroring IDA: this is the broken path production must avoid.
        FormToPySideWidget = TWidgetToQtPythonWidget

    class GraphViewer:  # noqa: N801 - keep IDA SWIG casing
        """Stand-in for idaapi.GraphViewer.

        Production overrides call self.Clear / AddNode / AddEdge / Refresh and
        index self[node_id]; these are provided as no-op stubs so __init__ and
        OnRefresh can be exercised without IDA.
        """

        def __init__(self, title: str = "") -> None:
            self._title = title
            self._nodes: list[Any] = []

        def Clear(self) -> None:  # noqa: N802 - keep IDA SWIG casing
            self._nodes = []

        def AddNode(self, node: Any) -> int:  # noqa: N802 - keep IDA SWIG casing
            self._nodes.append(node)
            return len(self._nodes) - 1

        def AddEdge(self, src: int, dst: int) -> None:  # noqa: N802 - keep IDA SWIG casing
            pass

        def Refresh(self) -> None:  # noqa: N802 - keep IDA SWIG casing
            pass

        def __getitem__(self, node_id: int) -> Any:
            return self._nodes[node_id]

    class Choose:  # noqa: N801 - keep IDA SWIG casing
        """Stand-in for idaapi.Choose so domain.chooser.MyChoose subclasses cleanly."""

        # Common Choose flags referenced by production code.
        CH_MODAL: int = 0x00000001
        # Column format flags (choose_column_type_t in IDA SDK). Production
        # code ORs widths with these (e.g. `10 | Choose.CHCOL_PLAIN`).
        CHCOL_PLAIN: int = 0x00000001

        def __init__(self, title: str = "", cols: list[Any] | None = None, **kwargs: Any) -> None:
            self._title = title
            self._cols = cols or []

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


# Qt binding modules that should only be mocked when NOT importable.
# If real PySide6/PyQt5 is installed, tests need the real classes (e.g.
# QAbstractTableModel) so production subclasses bind their real Python methods.
# A MagicMock-backed ``QtCore.QAbstractTableModel`` cannot be subclassed: the
# subclass's own methods get shadowed by the mock, so ``m.rowCount()`` returns
# a MagicMock instead of calling the user's implementation.
QT_MODULES: tuple[str, ...] = (
    "PySide6", "PySide6.QtCore", "PySide6.QtWidgets", "PySide6.QtGui",
    "PyQt5", "PyQt5.QtCore", "PyQt5.QtWidgets", "PyQt5.QtGui",
)


def _is_importable(mod_name: str) -> bool:
    """Return True if the top-level module can be imported."""
    top = mod_name.split(".", 1)[0]
    try:
        import importlib.util
        return importlib.util.find_spec(top) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def install() -> None:
    """Install all mock IDA modules into sys.modules. Idempotent.

    Qt bindings (PySide6/PyQt5) are only mocked when they are NOT importable
    in the current environment. When real Qt is present, tests run against it
    (use ``QT_QPA_PLATFORM=offscreen`` for headless runs); this is required for
    tests that subclass ``QAbstractTableModel`` and similar.
    """
    for mod_name in MOCK_MODULES:
        if mod_name in sys.modules:
            continue
        if mod_name in QT_MODULES and _is_importable(mod_name):
            continue
        # mypy: sys.modules is typed as dict[str, Module]; a MagicMock-backed
        # catch-all is intentional here. The mismatch is a known mypy limitation.
        sys.modules[mod_name] = _MockIdaModule()  # type: ignore[assignment]


def reset() -> None:
    """Reset mock state on all mock modules (between tests).

    Clears both call history AND configured return_value/side_effect so tests
    are fully isolated. Without ``return_value=True``, a test that sets
    ``idaapi.netnode.return_value = 42`` leaks the int into later tests, which
    then fail with ``AttributeError: 'int' object has no attribute 'supstr'``.
    ``MagicMock.reset_mock()`` only clears call history by default.
    """
    for mod_name in MOCK_MODULES:
        mod = sys.modules.get(mod_name)
        if mod is None:
            continue
        for attr_name in dir(mod):
            if attr_name.startswith("_"):
                continue
            attr = getattr(mod, attr_name, None)
            if isinstance(attr, MagicMock):
                attr.reset_mock(return_value=True, side_effect=True)
