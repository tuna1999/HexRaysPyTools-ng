"""``ScanObject`` (no 'd') and ``ScannedObject`` (with 'd') hierarchies.

Two layers of types live here:

* :class:`ScanObject` (no 'd') — what visitors **match** during traversal.
  Created from a cexpr; stateless + idempotent.
* :class:`ScannedObject` (with 'd') — what scanners **produce** when they
  find matches. Wraps a :class:`ScanObject` with the expression address,
  the function EA, an origin offset, and an :meth:`apply_type` callback.
  Lifetime-based: built when a match is found, ``apply_type()`` called later
  from the UI.

Keeping them separate: matching is stateless + idempotent (you can build one
from a cexpr and throw it away), while producing has lifetime (it remembers
what was found and where so the user can ``apply_type()`` it later).

Ported from the original ``api.py:13-205`` (~190 LOC for ``ScanObject``) and
``core/variable_scanner.py:19-114`` (~95 LOC for ``ScannedObject``).

The ``SO_*`` constants here are the canonical identifiers — both
``ScannedObject.create`` and ``is_legal_type`` checks depend on their numeric
values. Renumbering them would break saved netnode state.
"""
from __future__ import annotations

import logging
from typing import Any

import idaapi  # type: ignore[import-not-found]
import idc  # type: ignore[import-not-found]

from ...infra.arch.arch import to_hex

logger = logging.getLogger(__name__)

# Object-kind constants. The numeric values are part of the on-disk contract
# (they may be stored in netnodes from earlier versions). DO NOT renumber.
SO_LOCAL_VARIABLE = 1       # cexpr.op == idaapi.cot_var
SO_STRUCT_POINTER = 2       # cexpr.op == idaapi.cot_memptr
SO_STRUCT_REFERENCE = 3     # cexpr.op == idaapi.cot_memref
SO_GLOBAL_OBJECT = 4        # cexpr.op == idaapi.cot_obj
SO_CALL_ARGUMENT = 5        # cexpr.op == idaapi.cot_call
SO_MEMORY_ALLOCATOR = 6     # matches malloc/operator new
SO_RETURNED_OBJECT = 7      # matches the return value of a function


class ScanObject:
    """Base class for a single scanned item matched by ctree traversal.

    Subclasses populate ``id`` with one of the ``SO_*`` constants and override
    ``is_target`` for cexpr recognition. The base constructor leaves
    everything empty; subclasses call it and then set fields explicitly.
    """

    def __init__(self) -> None:
        self.ea: int = int(idaapi.BADADDR)
        self.name: str | None = None
        self.tinfo: idaapi.tinfo_t | None = None
        self.id: int = 0

    @staticmethod
    def create(cfunc: Any, arg: Any) -> ScanObject | None:
        """Build the right ``ScanObject`` subclass from a cexpr or ctree_item.

        Dispatches on ``arg.e.op`` (a ``cexpr_t``) or on ``arg`` being a
        ``ctree_item_t``. Returns ``None`` when the expression is not one of
        the recognized shapes — callers should treat ``None`` as "skip this
        item".
        """
        if isinstance(arg, idaapi.ctree_item_t):
            lvar = arg.get_lvar()
            if lvar:
                # Local variable — ctree_item_t carries the lvar directly.
                lvars = list(cfunc.get_lvars())
                index = lvars.index(lvar)
                lvar_obj = VariableObject(lvar, index)
                if arg.e is not None:
                    lvar_obj.ea = ScanObject.get_expression_address(cfunc, arg.e)
                return lvar_obj
            if int(arg.citype) != int(idaapi.VDI_EXPR):
                return None
            cexpr = arg.e
        else:
            cexpr = arg

        op = int(cexpr.op)
        result: ScanObject | None
        if op == int(idaapi.cot_var):
            lvar = cfunc.get_lvars()[int(cexpr.v.idx)]
            result = VariableObject(lvar, int(cexpr.v.idx))
            result.ea = ScanObject.get_expression_address(cfunc, cexpr)
            return result
        if op == int(idaapi.cot_memptr):
            pointed = cexpr.x.type.get_pointed_object()
            struct_name = pointed.dstr()
            result = StructPtrObject(struct_name, int(cexpr.m))
            result.name = _get_member_name(pointed, int(cexpr.m))
        elif op == int(idaapi.cot_memref):
            struct_t = cexpr.x.type
            struct_name = struct_t.dstr()
            result = StructRefObject(struct_name, int(cexpr.m))
            result.name = _get_member_name(struct_t, int(cexpr.m))
        elif op == int(idaapi.cot_obj):
            result = GlobalVariableObject(int(cexpr.obj_ea))
            result.name = idaapi.get_short_name(int(cexpr.obj_ea))
        else:
            return None

        assert result is not None  # mypy: covered by the elif chain above
        result.tinfo = cexpr.type
        result.ea = ScanObject.get_expression_address(cfunc, cexpr)
        return result

    @staticmethod
    def get_expression_address(cfunc: Any, cexpr: Any) -> int:
        """Walk parents until a real (non-BADADDR) cexpr.ea is found.

        Mirrors the original ``api.py:59-68``. Hex-Rays synthesises many
        sub-expressions without a back-reference to the assembly EA — those
        all carry ``BADADDR``. We bubble up through the ctree until we hit
        one that *does* have an EA, because that's the line of code the user
        wants to jump to.

        Returns ``idaapi.BADADDR`` if no ancestor has an address (rare; only
        happens for constants or synthetic top-level expressions).
        """
        expr = cexpr
        while expr is not None and int(expr.ea) == int(idaapi.BADADDR):
            expr = expr.to_specific_type
            parent = cfunc.body.find_parent_of(expr)
            if parent is None:
                return int(idaapi.BADADDR)
            expr = parent

        assert expr is not None  # parent of root expression is the function body
        return int(expr.ea)

    def is_target(self, cexpr: Any) -> bool:  # noqa: ARG002 - override in subclasses
        """Return True if ``cexpr`` represents this object."""
        return int(cexpr.op) == self.id

    def __hash__(self) -> int:
        return hash((self.id, self.name))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ScanObject):
            return NotImplemented
        return self.id == other.id and self.name == other.name

    def __repr__(self) -> str:
        return str(self.name) if self.name is not None else f"<ScanObject id={self.id}>"


class VariableObject(ScanObject):
    """Represents a ``var`` expression — a local variable reference.

    ``index`` is the slot in ``cfunc.get_lvars()`` (matches ``cexpr.v.idx``).
    """

    def __init__(self, lvar: Any, index: int) -> None:
        super().__init__()
        self.lvar = lvar
        self.tinfo = lvar.type()
        self.name = str(lvar.name)
        self.index = index
        self.id = SO_LOCAL_VARIABLE

    def is_target(self, cexpr: Any) -> bool:
        return int(cexpr.op) == int(idaapi.cot_var) and int(cexpr.v.idx) == self.index


class StructPtrObject(ScanObject):
    """Represents an ``x->m`` expression — pointer dereference + member access.

    ``struct_name`` is the *pointed-to* type's display string (``type.dstr()``
    after stripping the pointer). Equality is by name+offset — two accesses
    to the same field on the same struct type match.
    """

    def __init__(self, struct_name: str, offset: int) -> None:
        super().__init__()
        self.struct_name = struct_name
        self.offset = offset
        self.id = SO_STRUCT_POINTER

    def is_target(self, cexpr: Any) -> bool:
        return (
            int(cexpr.op) == int(idaapi.cot_memptr)
            and int(cexpr.m) == self.offset
            and str(cexpr.x.type.get_pointed_object().dstr()) == self.struct_name
        )


class StructRefObject(ScanObject):
    """Represents an ``x.m`` expression — value (not pointer) member access."""

    def __init__(self, struct_name: str, offset: int) -> None:
        super().__init__()
        self.struct_name = struct_name
        self.offset = offset
        self.id = SO_STRUCT_REFERENCE

    def is_target(self, cexpr: Any) -> bool:
        return (
            int(cexpr.op) == int(idaapi.cot_memref)
            and int(cexpr.m) == self.offset
            and str(cexpr.x.type.dstr()) == self.struct_name
        )


class GlobalVariableObject(ScanObject):
    """Represents a global object reference (``cot_obj`` with an obj_ea)."""

    def __init__(self, object_address: int) -> None:
        super().__init__()
        self.obj_ea = object_address
        self.id = SO_GLOBAL_OBJECT

    def is_target(self, cexpr: Any) -> bool:
        return (
            int(cexpr.op) == int(idaapi.cot_obj)
            and self.obj_ea == int(cexpr.obj_ea)
        )


class CallArgObject(ScanObject):
    """Represents a call to a specific function, scoped to one argument.

    Two-stage factory:
    - ``CallArgObject(func_ea, arg_idx)`` — raw construction
    - ``CallArgObject.create(cfunc, arg_idx)`` — built from a function's arg
      slot (used by ``RecursiveObjectUpwardsVisitor`` to scan callers).
    - ``create_scan_obj(cfunc, cexpr)`` — drill through pointer casts/refs/
      adds/subs/indices to find the underlying ``ScanObject`` for the actual
      expression at the call site.
    """

    def __init__(self, func_address: int, arg_idx: int) -> None:
        super().__init__()
        self.func_ea = func_address
        self.arg_idx = arg_idx
        self.id = SO_CALL_ARGUMENT

    def is_target(self, cexpr: Any) -> bool:
        return (
            int(cexpr.op) == int(idaapi.cot_call)
            and int(cexpr.x.obj_ea) == self.func_ea
        )

    def create_scan_obj(self, cfunc: Any, cexpr: Any) -> ScanObject | None:
        """Drill through cast/ref/add/sub/idx to the underlying expression.

        When a function takes a ``void *`` and the caller passes a struct
        pointer, the ctree looks like ``call((cast)((add)(var, idx)))``. The
        caller wants to track the inner ``var``, not the synthesized call —
        we walk down until we hit a base expression.
        """
        e = cexpr.a[self.arg_idx]
        while int(e.op) in (
            int(idaapi.cot_cast),
            int(idaapi.cot_ref),
            int(idaapi.cot_add),
            int(idaapi.cot_sub),
            int(idaapi.cot_idx),
        ):
            e = e.x
        return ScanObject.create(cfunc, e)

    @staticmethod
    def create(cfunc: Any, arg_idx: int) -> CallArgObject:
        """Build a CallArgObject from a function's arg slot."""
        result = CallArgObject(int(cfunc.entry_ea), arg_idx)
        result.name = str(cfunc.get_lvars()[arg_idx].name)
        result.tinfo = cfunc.type
        return result

    def __repr__(self) -> str:
        return str(self.name) if self.name is not None else f"<CallArgObject idx={self.arg_idx}>"


class ReturnedObject(ScanObject):
    """Represents the value returned by a specific function."""

    def __init__(self, func_address: int) -> None:
        super().__init__()
        self._func_ea = func_address
        self.id = SO_RETURNED_OBJECT

    def is_target(self, cexpr: Any) -> bool:
        return (
            int(cexpr.op) == int(idaapi.cot_call)
            and int(cexpr.x.obj_ea) == self._func_ea
        )


class MemoryAllocationObject(ScanObject):
    """Represents an ``operator new()`` or ``malloc()`` call.

    Detection is by substring match on the called function's short name
    (``"malloc"`` or ``"operator new"``). The ``size`` field is read from
    the first argument when it's a numeric literal — otherwise 0.
    """

    def __init__(self, name: str, size: int) -> None:
        super().__init__()
        self.name = name
        self.size = size
        self.id = SO_MEMORY_ALLOCATOR

    @staticmethod
    def create(cfunc: Any, cexpr: Any) -> MemoryAllocationObject | None:
        """Build a MemoryAllocationObject from a call expression (or cast-wrapped call)."""
        if int(cexpr.op) == int(idaapi.cot_call):
            e = cexpr
        elif int(cexpr.op) == int(idaapi.cot_cast) and int(cexpr.x.op) == int(idaapi.cot_call):
            e = cexpr.x
        else:
            return None

        func_name = idaapi.get_short_name(int(e.x.obj_ea))
        if "malloc" in func_name or "operator new" in func_name:
            carg = e.a[0]
            size = int(carg.numval()) if int(carg.op) == int(idaapi.cot_num) else 0
            result = MemoryAllocationObject(func_name, size)
            result.ea = ScanObject.get_expression_address(cfunc, e)
            return result
        return None


# --- helpers ------------------------------------------------------------------


def _get_member_name(struct_tinfo: Any, offset: int) -> str:
    """Get the member name at byte ``offset`` of struct ``struct_tinfo``.

    Mirrors ``helper.get_member_name`` from the original. The offset is in
    bytes (we convert to bits for the IDA API).
    """
    udt_member = idaapi.udt_member_t()
    udt_member.offset = offset * 8
    if struct_tinfo.find_udt_member(udt_member, idaapi.STRMEM_OFFSET) == -1:
        return ""
    return str(udt_member.name)


# === ScannedObject (with 'd') hierarchy =======================================
#
# What the scanner PRODUCES. Wraps a ScanObject with the expression address,
# the function EA (computed via idc.get_func_attr), an origin offset, and an
# apply_type() callback for the UI to call later.
#
# Equality + hash are by (func_ea, name, expression_address) — the same match
# found at the same line is the same ScannedObject, even if the origin offset
# differs (which happens for global objects).


class ScannedObject:
    """Base for a scanned item — wraps a matching :class:`ScanObject`.

    The scanner creates one of these when it finds a match; the UI calls
    :meth:`apply_type` later to actually set the type on the variable / global.

    ``_applicable`` is set to ``False`` when the scanner is traversing a
    "crippled" function (a single-call or single-return thunk) — in that case
    the type belongs to the caller, not this passthrough, so we skip
    application.
    """

    def __init__(
        self,
        name: str,
        expression_address: int,
        origin: int,
        applicable: bool = True,
    ) -> None:
        self.name = name
        self.expression_address = int(expression_address)
        # func_ea is derived from the expression address via the active
        # function list. Mirrors `idc.get_func_attr(ea, FUNCATTR_START)`.
        self.func_ea = int(
            idc.get_func_attr(int(expression_address), idc.FUNCATTR_START)
        )
        self.origin = int(origin)
        self._applicable = bool(applicable)

    @property
    def function_name(self) -> str:
        """Return ``idaapi.get_short_name(func_ea)`` for display in the UI."""
        return str(idaapi.get_short_name(int(self.func_ea)))

    def apply_type(self, tinfo: Any) -> None:
        """Apply ``tinfo`` to this scanned variable. Subclasses override."""
        raise NotImplementedError

    @staticmethod
    def create(
        obj: Any,
        expression_address: int,
        origin: int,
        applicable: bool,
    ) -> ScannedObject:
        """Build the right ``ScannedObject`` subclass from a matching :class:`ScanObject`.

        Dispatches on ``obj.id`` (``SO_GLOBAL_OBJECT``, ``SO_LOCAL_VARIABLE``,
        or one of the struct-member kinds). Raises :class:`AssertionError` for
        other kinds — only match-producing :class:`ScanObject` subclasses
        participate in the production layer.
        """
        if obj.id == SO_GLOBAL_OBJECT:
            return ScannedGlobalObject(
                int(obj.ea), obj.name, expression_address, origin, applicable
            )
        if obj.id == SO_LOCAL_VARIABLE:
            return ScannedVariableObject(
                obj.lvar, obj.name, expression_address, origin, applicable
            )
        if obj.id in (SO_STRUCT_REFERENCE, SO_STRUCT_POINTER):
            return ScannedStructureMemberObject(
                obj.struct_name,
                int(obj.offset),
                obj.name,
                expression_address,
                origin,
                applicable,
            )
        raise AssertionError(f"Cannot create ScannedObject for obj.id={obj.id}")

    def to_list(self) -> list[str]:
        """Row representation for the chooser viewer.

        Columns: ``origin`` (hex), ``function_name``, ``name``,
        ``expression_address`` (hex via :func:`to_hex`).
        """
        return [
            f"0x{int(self.origin):04X}",
            self.function_name,
            str(self.name),
            to_hex(int(self.expression_address)),
        ]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ScannedObject):
            return NotImplemented
        return (
            int(self.func_ea) == int(other.func_ea)
            and str(self.name) == str(other.name)
            and int(self.expression_address) == int(other.expression_address)
        )

    def __hash__(self) -> int:
        return hash((int(self.func_ea), str(self.name), int(self.expression_address)))

    def __repr__(self) -> str:
        return f"{str(self.name)} : {to_hex(int(self.expression_address))}"


class ScannedGlobalObject(ScannedObject):
    """A scanned global variable (``cot_obj``).

    ``apply_type`` writes the tinfo to the global's address via
    :func:`idaapi.set_tinfo`.
    """

    def __init__(
        self,
        obj_ea: int,
        name: str,
        expression_address: int,
        origin: int,
        applicable: bool = True,
    ) -> None:
        super().__init__(name, expression_address, origin, applicable)
        self._obj_ea = int(obj_ea)

    def apply_type(self, tinfo: Any) -> None:
        if not self._applicable:
            return
        idaapi.set_tinfo(int(self._obj_ea), tinfo)


class ScannedVariableObject(ScannedObject):
    """A scanned local variable.

    ``apply_type`` opens the function's pseudocode window, finds the lvar by
    :class:`idaapi.lvar_locator_t` (location + definition ea — survives
    re-decompiles), and writes the tinfo via ``set_lvar_type``.
    """

    def __init__(
        self,
        lvar: Any,
        name: str,
        expression_address: int,
        origin: int,
        applicable: bool = True,
    ) -> None:
        super().__init__(name, expression_address, origin, applicable)
        # Store a locator (location + defea) so we can match the lvar in the
        # pseudocode window after it has been re-opened — the original lvar
        # pointer becomes stale across window opens.
        self._lvar_locator = idaapi.lvar_locator_t(lvar.location, lvar.defea)

    def apply_type(self, tinfo: Any) -> None:
        if not self._applicable:
            return

        hx_view = idaapi.open_pseudocode(int(self.func_ea), -1)
        if hx_view is None:
            logger.warning(
                "Failed to open pseudocode for func %s", to_hex(int(self.func_ea))
            )
            return
        try:
            lvars = list(hx_view.cfunc.get_lvars())
            # Find the lvar whose locator matches — ``==`` on lvar_t compares
            # location + defea (the locator fields).
            match = next(
                (lv for lv in lvars if lv == self._lvar_locator),
                None,
            )
            if match is not None:
                logger.debug(
                    "Applying tinfo to %s in %s",
                    str(self.name), self.function_name,
                )
                hx_view.set_lvar_type(match, tinfo)
            else:
                logger.warning(
                    "Failed to find previously scanned local variable %s from %s",
                    str(self.name), to_hex(int(self.expression_address)),
                )
        finally:
            # The pseudocode window we opened is borrowed — don't close it,
            # IDA owns the lifetime. The original plugin didn't close it
            # either (verified in refs/.../variable_scanner.py:96-102).
            pass


class ScannedStructureMemberObject(ScannedObject):
    """A scanned struct field reference.

    ``apply_type`` is currently a no-op (the original just logs a warning) —
    changing the type of a struct field is non-trivial because other code
    may already reference it; the UI workflow instead commits the whole
    rebuilt struct via :class:`StructureModel.import_to_structures`.
    """

    def __init__(
        self,
        struct_name: str,
        struct_offset: int,
        name: str,
        expression_address: int,
        origin: int,
        applicable: bool = True,
    ) -> None:
        super().__init__(name, expression_address, origin, applicable)
        self._struct_name = str(struct_name)
        self._struct_offset = int(struct_offset)

    def apply_type(self, tinfo: Any) -> None:  # noqa: ARG002 - tinfo unused (see docstring)
        if not self._applicable:
            return
        logger.warning(
            "Changing type of structure field is not yet implemented. Address - %s",
            to_hex(int(self.expression_address)),
        )
