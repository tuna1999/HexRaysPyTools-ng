"""ctree visitor base classes for the struct-reconstruction scanner.

Ported from the original ``api.py:211-580``. Provides the
ctree-parentee-t visitor hierarchy that the scanner engine uses to walk a
decompiled function and extract struct member candidates.

Five layers of visitors live here:

* :class:`ObjectVisitor` (base) — owns the tracked-objects list and the
  apply-callback. Subclasses override :meth:`_manipulate` to react to each
  matched expression.
* :class:`ObjectDownwardsVisitor` — *forward* traversal: follows the
  assignment chain downstream (``a = tracked`` ⇒ track ``a`` too).
* :class:`ObjectUpwardsVisitor` — *backward* traversal: builds a
  from→to assignment graph, then re-traverses to find what feeds the
  tracked object.
* :class:`RecursiveObjectVisitor` (base for cross-function) + the two
  concrete recursive variants (:class:`RecursiveObjectDownwardsVisitor`,
  :class:`RecursiveObjectUpwardsVisitor`) — walk across function
  boundaries by decompiling callees/callers.

All visitors operate on live Hex-Rays ctree objects — this module is not
unit-testable end-to-end with mocks, so it is excluded from the coverage
gate (``pyproject.toml``).
"""

from __future__ import annotations

import logging
from typing import Any

import idaapi  # type: ignore[import-not-found]

from ...infra.arch.arch import (
    get_funcs_calling_address,
    is_imported_ea,
    to_hex,
)
from ..types.func_type import get_call_argument_info
from .helpers import decompile_function
from .scanned_object import (
    SO_CALL_ARGUMENT,
    SO_RETURNED_OBJECT,
    CallArgObject,
    ScanObject,
    VariableObject,
)

logger = logging.getLogger(__name__)


class ObjectVisitor(idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Base visitor: walk a cfunc, tracking a set of :class:`ScanObject`s.

    Subclasses override :meth:`_manipulate(cexpr, obj)` to react when an
    expression matches a tracked object. The :attr:`_objects` list grows as
    the visitor discovers new objects derived from the initial one.

    Set :attr:`_skip=True` to start the visitor in "seek mode" — no
    tracking or :meth:`_manipulate` calls fire until the initial object
    itself is encountered. This is how the scanner engine scopes its work
    to the expression the user clicked on.
    """

    def __init__(self, cfunc: Any, obj: Any, data: Any, skip_until_object: bool) -> None:
        super().__init__()
        self._cfunc = cfunc
        self._objects: list[Any] = [obj]
        self._init_obj = obj
        self._data = data
        self._start_ea: int = int(obj.ea) if obj is not None else int(idaapi.BADADDR)
        self._skip: bool = (
            bool(skip_until_object) if self._start_ea != int(idaapi.BADADDR) else False
        )
        self.crippled: bool = False
        # Default callback bound to the instance — set_callbacks can swap this.
        self._user_manipulate = self._default_manipulate

    def process(self) -> None:
        """Run the visitor over the cfunc body."""
        self.apply_to(self._cfunc.body, None)

    def set_callbacks(self, manipulate: Any = None) -> None:
        """Override the default ``_manipulate`` callback at runtime.

        The original plugin uses this to inject per-instance behavior
        without subclassing. Used by the scanner engine to plug its own
        ``_manipulate`` into a generic :class:`ObjectDownwardsVisitor`.
        """
        if manipulate is not None:
            self._user_manipulate = manipulate.__get__(self, type(self))

    def _get_line(self) -> str:
        """Return the decompiled text of the enclosing citem.

        Walks the parents stack until it hits a citem (not a cexpr) — the
        citem is the statement level (assignment, if, return, ...).
        :func:`idaapi.tag_remove` strips IDA's color codes so the result is
        human-readable.
        """
        for p in reversed(self.parents):
            if not p.is_expr():
                return str(idaapi.tag_remove(p.print1(self._cfunc)))
        # Original raises AssertionError; we return a sentinel so callers
        # can log without crashing the whole scan if the ctree shape is
        # unusual.
        return ""

    def _manipulate(self, cexpr: Any, obj: Any) -> None:
        """Per-item callback. Subclasses override for real work.

        Default behaviour: delegate to whatever ``set_callbacks`` installed
        (or fall back to a debug log when no callback was set).
        """
        self._user_manipulate(cexpr, obj)

    def _default_manipulate(self, cexpr: Any, obj: Any) -> None:
        """Fallback manipulator: log the match and move on."""
        logger.debug(
            "ObjectVisitor default _manipulate: obj.id=%d expr.op=%d",
            int(obj.id),
            int(cexpr.op),
        )

    def _is_initial_object(self, cexpr: Any) -> bool:
        """True if ``cexpr`` is the expression the user selected.

        Used by ``_skip`` mode to know when to start tracking. The base
        class does the obvious check (obj matches + EA matches the start).
        Subclasses may override to handle ``cot_asg`` / ``cot_cast`` shape
        variations (e.g. the user clicked the LHS of an assignment).
        """
        from .ctree_utils import find_asm_address

        return (
            self._init_obj.is_target(cexpr)
            and find_asm_address(cexpr, self.parents) == self._start_ea
        )

    @property
    def objects(self) -> list[Any]:
        """Snapshot of the currently-tracked objects (read-only copy)."""
        return list(self._objects)


class ObjectDownwardsVisitor(ObjectVisitor):
    """Forward visitor: follow assignments **downstream** from the start.

    The visitor's job is to discover every name the tracked object is
    *assigned into* and to fire :meth:`_manipulate` for every place any
    tracked object is used. Concretely, given::

        v1 = tracked;        # _skip until here
        v2 = v1;             # track v2 too
        v1 = something_else; # v1 is overwritten — drop it
        use(v2);             # _manipulate fires for v2

    the visitor ends with ``_objects = [v2]`` (or v1 was removed) and
    :meth:`_manipulate` fired once for the ``use(v2)`` cexpr.

    Subclasses (the scanner engine) override :meth:`_manipulate` to record
    the matched expression.
    """

    def __init__(
        self, cfunc: Any, obj: Any, data: Any = None, skip_until_object: bool = False
    ) -> None:
        super().__init__(cfunc, obj, data, skip_until_object)
        # CV_POST makes IDA call leave_expr after every expression's children
        # are processed. We need both visit_expr (to extend the tracked set)
        # and leave_expr (to fire _manipulate on terminal uses).
        self.cv_flags |= int(idaapi.CV_POST)

    def visit_expr(self, cexpr: Any) -> int:
        if self._skip:
            if self._is_initial_object(cexpr):
                self._skip = False
            else:
                return 0

        if int(cexpr.op) != int(idaapi.cot_asg):
            return 0

        x_cexpr = cexpr.x
        y_cexpr = cexpr.y.x if int(cexpr.y.op) == int(idaapi.cot_cast) else cexpr.y

        for obj in self._objects:
            if obj.is_target(x_cexpr):
                # tracked object is being overwritten — check whether the
                # new value still references any tracked object
                if self._is_object_overwritten(x_cexpr, obj, y_cexpr):
                    logger.info("Removed object id=%d from scanning", int(obj.id))
                    self._objects.remove(obj)
                return 0
            if obj.is_target(y_cexpr):
                # `tracked = something` — track the new LHS too
                new_obj = ScanObject.create(self._cfunc, x_cexpr)
                if new_obj is not None:
                    self._objects.append(new_obj)
                return 0
        return 0

    def leave_expr(self, cexpr: Any) -> int:
        if self._skip:
            return 0
        for obj in self._objects:
            if obj.is_target(cexpr) and int(obj.id) != int(SO_RETURNED_OBJECT):
                self._manipulate(cexpr, obj)
                return 0
        return 0

    def _is_initial_object(self, cexpr: Any) -> bool:
        """Match the initial object, allowing for ``x = obj`` and ``x = (cast)obj`` shapes."""
        if int(cexpr.op) == int(idaapi.cot_asg):
            cexpr = cexpr.y
            if int(cexpr.op) == int(idaapi.cot_cast):
                cexpr = cexpr.x
        return super()._is_initial_object(cexpr)

    def _is_object_overwritten(self, x_cexpr: Any, obj: Any, y_cexpr: Any) -> bool:
        """Decide whether ``obj = y_cexpr`` is a real overwrite.

        If ``y_cexpr`` is ``other_tracked``, the LHS is being assigned
        FROM a still-tracked object, not really overwritten — keep
        ``obj`` in the tracked set. Otherwise (literal, call to an
        untracked function, etc.) the old value is gone — drop ``obj``.
        """
        if len(self._objects) < 2:
            return False
        e = y_cexpr.x if int(y_cexpr.op) == int(idaapi.cot_cast) else y_cexpr
        if int(e.op) != int(idaapi.cot_call) or len(e.a) == 0:
            return True
        return all(not tracked.is_target(e.a[0]) for tracked in self._objects)


class ObjectUpwardsVisitor(ObjectVisitor):
    """Backward visitor: build a from→to assignment graph, then parse it.

    Used by :class:`GuessAllocation` (Phase B.7) to find where the tracked
    object came from. Two passes:

    1. **STAGE_PREPARE** — record every assignment ``a = b`` so we know
       the data flow.
    2. **STAGE_PARSING** — re-traverse; :meth:`_manipulate` fires for any
       cexpr whose object is in the closed dependency set (i.e. anything
       that transitively feeds the initial object).
    """

    STAGE_PREPARE = 1
    STAGE_PARSING = 2

    def __init__(
        self, cfunc: Any, obj: Any, data: Any = None, skip_after_object: bool = False
    ) -> None:
        super().__init__(cfunc, obj, data, skip_after_object)
        self._stage: int = self.STAGE_PREPARE
        self._tree: dict[Any, set[Any]] = {}
        # _call_obj is the seed for upward-visiting call sites
        # (RecursiveObjectUpwardsVisitor sets it; this base class leaves it None)
        self._call_obj = obj if int(obj.id) == 5 else None  # SO_CALL_ARGUMENT = 5

    def visit_expr(self, cexpr: Any) -> int:
        if self._stage == self.STAGE_PARSING:
            return 0

        if self._call_obj is not None and self._call_obj.is_target(cexpr):
            obj = self._call_obj.create_scan_obj(self._cfunc, cexpr)
            if obj is not None:
                self._objects.append(obj)
            return 0

        if int(cexpr.op) != int(idaapi.cot_asg):
            return 0

        x_cexpr = cexpr.x
        y_cexpr = cexpr.y.x if int(cexpr.y.op) == int(idaapi.cot_cast) else cexpr.y

        obj_left = ScanObject.create(self._cfunc, x_cexpr)
        obj_right = ScanObject.create(self._cfunc, y_cexpr)
        if obj_left is not None and obj_right is not None:
            self._add_object_assignment(obj_left, obj_right)

        if self._skip and self._is_initial_object(cexpr):
            return 1
        return 0

    def leave_expr(self, cexpr: Any) -> int:
        if self._stage == self.STAGE_PREPARE:
            return 0

        if self._skip and self._is_initial_object(cexpr):
            self._manipulate(cexpr, self._init_obj)
            return 1

        for obj in self._objects:
            if obj.is_target(cexpr):
                self._manipulate(cexpr, obj)
                return 0
        return 0

    def process(self) -> None:
        """Run the two-stage traversal (prepare + parse)."""
        self._stage = self.STAGE_PREPARE
        self.cv_flags &= ~int(idaapi.CV_POST)
        super().process()
        self._stage = self.STAGE_PARSING
        self.cv_flags |= int(idaapi.CV_POST)
        self._prepare()
        super().process()

    def _add_object_assignment(self, from_obj: Any, to_obj: Any) -> None:
        if from_obj in self._tree:
            self._tree[from_obj].add(to_obj)
        else:
            self._tree[from_obj] = {to_obj}

    def _prepare(self) -> None:
        """Compute the transitive closure of objects feeding the initial one.

        BFS through ``_tree`` starting from the initial objects. The result
        is the set of every object that transitively feeds the initial one
        (i.e. everything that could be the source of the initial object's
        value). Cleared ``_tree`` after computing the closure.
        """
        result: set[Any] = set()
        todo: set[Any] = set(self._objects)
        while todo:
            obj = todo.pop()
            result.add(obj)
            if int(obj.id) == 5 or obj not in self._tree:  # SO_CALL_ARGUMENT = 5
                continue
            downstream = self._tree[obj]
            todo |= downstream - result
            result |= downstream
        self._objects = list(result)
        self._tree.clear()


# --- Recursive (cross-function) visitors -------------------------------------


class RecursiveObjectVisitor(ObjectVisitor):
    """Base for cross-function visitors.

    Subclasses (:class:`RecursiveObjectDownwardsVisitor`,
    :class:`RecursiveObjectUpwardsVisitor`) walk across function
    boundaries by decompiling callees/callers. A ``_visited`` set of
    ``(func_ea, arg_idx)`` tuples prevent infinite recursion; a
    ``_new_for_visit`` queue collects ``(func_ea, arg_idx, sub_offset)``
    triples discovered during one pass and is drained afterward. The
    optional ``sub_offset`` (added for sub-region calls like
    ``helper(&obj->u)``) is the extra offset the callee's argument
    pointer sits at within the parent's struct — the drain sets it as
    ``self._origin`` so the callee scan emits members at the correct
    absolute offset.

    The four lifecycle hooks (``_start``, ``_start_iteration``,
    ``_finish``, ``_finish_iteration``) let subclasses inject per-function
    setup/teardown without overriding :meth:`process`.
    """

    def __init__(
        self,
        cfunc: Any,
        obj: Any,
        data: Any = None,
        skip_until_object: bool = False,
        visited: set[tuple[int, int]] | None = None,
        imported_ea: set[int] | None = None,
    ) -> None:
        super().__init__(cfunc, obj, data, skip_until_object)
        self._visited: set[tuple[int, int]] = visited if visited else set()
        self._new_for_visit: set[tuple[int, int, int]] = set()
        self.crippled = False
        self._arg_idx: int = -1
        # Session-owned import cache (replaces the original cache.imported_ea
        # global). Callers pass session.imported_ea so recursive scans can
        # skip imported (PLT) call targets.
        self._imported_ea: set[int] = imported_ea if imported_ea is not None else set()
        # Debug scan-tree (logging only — not part of the algorithm).
        self._debug_scan_tree: dict[tuple[str, int], set[tuple[str, int]]] = {}
        self._debug_scan_tree_root: str = ""
        self._debug_message: list[str] = []

    def set_callbacks(
        self,
        manipulate: Any = None,
        start: Any = None,
        start_iteration: Any = None,
        finish: Any = None,
        finish_iteration: Any = None,
    ) -> None:
        """Override any of the 5 lifecycle hooks at runtime.

        Each hook is replaced by a bound method of the passed-in function.
        ``# type: ignore[method-assign]`` is intentional — swapping a
        method at runtime is a deliberate plugin pattern (the original
        does the same) that mypy cannot model.
        """
        super().set_callbacks(manipulate)
        if start is not None:
            self._start = start.__get__(self, type(self))  # type: ignore[method-assign]
        if start_iteration is not None:
            self._start_iteration = start_iteration.__get__(self, type(self))  # type: ignore[method-assign]
        if finish is not None:
            self._finish = finish.__get__(self, type(self))  # type: ignore[method-assign]
        if finish_iteration is not None:
            self._finish_iteration = finish_iteration.__get__(self, type(self))  # type: ignore[method-assign]

    def prepare_new_scan(self, cfunc: Any, arg_idx: int, obj: Any, skip: bool = False) -> None:
        """Reset per-function state for a fresh callee/caller scan."""
        self._cfunc = cfunc
        self._arg_idx = arg_idx
        self._objects = [obj]
        self._init_obj = obj
        self._skip = False
        self.crippled = self._is_func_crippled()

    def process(self) -> None:
        """Run the full recursive scan: start → iterate → finish → log."""
        self._start()
        self._recursive_process()
        self._finish()
        self._dump_scan_tree()

    def _recursive_process(self) -> None:
        """One iteration: per-function setup, walk, per-function teardown."""
        self._start_iteration()
        super().process()
        self._finish_iteration()

    def _manipulate(self, cexpr: Any, obj: Any) -> None:
        # _check_call collects callee/caller targets BEFORE the real
        # manipulation runs, so the recursive drain sees them.
        self._check_call(cexpr)
        super()._manipulate(cexpr, obj)

    def _check_call(self, cexpr: Any) -> None:
        """Detect calls worth recursing into. Subclasses override."""
        raise NotImplementedError("Subclasses must implement _check_call")

    def _add_visit(self, func_ea: int, arg_idx: int, sub_offset: int = 0) -> bool:
        """Record a (func, arg, sub_offset) to recurse into. Returns True if new.

        ``sub_offset`` is the byte offset the callee's argument pointer
        sits at within the parent's struct (0 for direct-arg calls,
        non-zero for sub-region calls like ``helper(&obj->u)``). The
        drain sets it as the scan origin so the callee scan emits
        members at the correct absolute offset.
        """
        visit_key = (int(func_ea), int(arg_idx))
        if visit_key in self._visited:
            return False
        self._visited.add(visit_key)
        self._new_for_visit.add((int(func_ea), int(arg_idx), int(sub_offset)))
        return True

    def _add_scan_tree_info(self, func_ea: int, arg_idx: int, sub_offset: int = 0) -> None:
        """Append a node to the debug scan-tree (for logging)."""
        try:
            head_node = (idaapi.get_name(int(self._cfunc.entry_ea)), self._arg_idx)
            tail_node = (idaapi.get_name(int(func_ea)), int(arg_idx))
        except Exception:  # noqa: BLE001 — debug logging must never crash the scan
            return
        self._debug_scan_tree.setdefault(head_node, set()).add(tail_node)

    def _dump_scan_tree(self) -> None:
        """Pretty-print the recursive scan tree at DEBUG level."""
        self._debug_scan_tree_root = idaapi.get_name(int(self._cfunc.entry_ea))
        self._debug_message = [f"--- Scan Tree---\n{self._debug_scan_tree_root}"]
        self._prepare_debug_message()
        if self._debug_message:
            logger.debug("%s\n---------------", "\n".join(self._debug_message))

    def _prepare_debug_message(self, key: tuple[str, int] | None = None, level: int = 1) -> None:
        if key is None:
            key = (self._debug_scan_tree_root, -1)
        if key in self._debug_scan_tree:
            for func_name, arg_idx in self._debug_scan_tree[key]:
                prefix = " | " * (level - 1) + " |_ "
                self._debug_message.append(f"{prefix}{func_name} (idx: {arg_idx})")
                self._prepare_debug_message((func_name, arg_idx), level + 1)

    def _is_func_crippled(self) -> bool:
        """True if the function body is just a thunk (single return / single call).

        Crippled functions propagate the object unchanged, so the scanner
        skips applying a type when it sees one (the type belongs to the
        caller, not this passthrough).
        """
        b = self._cfunc.body.cblock
        if b.size() == 1:
            e = b.at(0)
            return int(e.op) == int(idaapi.cit_return) or (
                int(e.op) == int(idaapi.cit_expr) and int(e.cexpr.op) == int(idaapi.cot_call)
            )
        return False

    # Lifecycle hooks (no-ops by default; subclasses or set_callbacks override).
    def _start(self) -> None:
        """Called once at the start of the whole recursive scan."""

    def _start_iteration(self) -> None:
        """Called before each individual function is walked."""

    def _finish(self) -> None:
        """Called once after all recursion completes."""

    def _finish_iteration(self) -> None:
        """Called after each individual function is walked."""


class RecursiveObjectDownwardsVisitor(RecursiveObjectVisitor, ObjectDownwardsVisitor):
    """Recursive forward visitor: also walk into callees.

    When the tracked object is passed as an argument to a call, decompile
    the callee and scan it (the callee's argument lvar becomes the new
    seed). Mirrors the original ``RecursiveObjectDownwardsVisitor``.
    """

    def __init__(
        self,
        cfunc: Any,
        obj: Any,
        data: Any = None,
        skip_until_object: bool = False,
        visited: set[tuple[int, int]] | None = None,
        imported_ea: set[int] | None = None,
    ) -> None:
        super().__init__(cfunc, obj, data, skip_until_object, visited, imported_ea)

    def _check_call(self, cexpr: Any) -> None:
        """If the tracked object is a call argument, queue the callee for scanning.

        Recognises two call-arg shapes (the tracked object is ``obj``):
          * ``callee(obj)`` — direct arg
          * ``callee((T)obj)`` — cast-wrapped arg

        Sub-region shapes (``callee(obj + off)``, ``callee(&obj->u)``) were
        explored in segment 3 iteration 4 but introduced over-matching
        noise on the fixture without metric gain (strict offset+size
        scorer cannot credit nested UDT sub-structures, and ``_origin``
        propagation in the same visitor instance is fragile under mixed
        queue contents). The 3-tuple queue shape carries a ``sub_offset``
        slot for future use.
        """
        parent = self.parent_expr()
        if parent is None:
            return
        parents_size = int(self.parents.size())
        grandparent = self.parents.at(parents_size - 2) if parents_size >= 2 else None

        call_cexpr: Any = None
        arg_cexpr: Any = None
        sub_offset: int = 0

        if int(parent.op) == int(idaapi.cot_call):
            call_cexpr = parent
            arg_cexpr = cexpr
        elif (
            grandparent is not None
            and int(parent.op) == int(idaapi.cot_cast)
            and int(grandparent.cexpr.op) == int(idaapi.cot_call)
        ):
            call_cexpr = grandparent.cexpr
            arg_cexpr = parent
        else:
            return
        # Only cot_obj carries an address; indirect calls have a typed callee
        # expression but no concrete function to recurse into.
        if int(call_cexpr.x.op) != int(idaapi.cot_obj):
            return
        idx, _ = get_call_argument_info(call_cexpr, arg_cexpr)
        if idx == -1:
            logger.debug(
                "[HexRaysPyTools][Deep Scan Call] caller=0x%X skipped: argument index not found",
                int(self._cfunc.entry_ea),
            )
            return
        func_ea = int(call_cexpr.x.obj_ea)
        if func_ea == int(idaapi.BADADDR):
            logger.debug(
                "[HexRaysPyTools][Deep Scan Call] caller=0x%X arg=%d skipped: indirect/BADADDR target",
                int(self._cfunc.entry_ea),
                idx,
            )
            return
        if self._add_visit(func_ea, idx, sub_offset):
            logger.debug(
                "[HexRaysPyTools][Deep Scan Call] caller=0x%X -> callee=0x%X arg=%d",
                int(self._cfunc.entry_ea),
                func_ea,
                idx,
            )
            self._add_scan_tree_info(func_ea, idx, sub_offset)
        else:
            logger.debug(
                "[HexRaysPyTools][Deep Scan Call] caller=0x%X -> callee=0x%X arg=%d skipped: already visited",
                int(self._cfunc.entry_ea),
                func_ea,
                idx,
            )

    def _maybe_follow_thunk(self) -> None:
        """Follow an argumentless tail-call thunk: ``return callee();``.

        Compilers (gcc -O2 tail calls) turn wrappers into thunks whose ctree
        shows no argument use at all — the object is forwarded in a register,
        so a scan of the thunk finds nothing. When the sole statement is a
        zero-argument tail call, the seed argument register reaches the
        callee unchanged (ABI passthrough — exactly what a reverse engineer
        follows manually), so queue the callee's matching argument.
        """
        if self._visited or not self._is_func_crippled():
            return
        stmt = self._cfunc.body.cblock.at(0)
        call = None
        try:
            if int(stmt.op) == int(idaapi.cit_return):
                call = stmt.creturn.expr
            elif int(stmt.op) == int(idaapi.cit_expr):
                call = stmt.cexpr
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return
        if call is None or int(call.op) != int(idaapi.cot_call):
            return
        try:
            if int(call.a.size()) != 0:
                return  # visible argument — the normal _check_call path owns it
            func_ea = int(call.x.obj_ea)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return
        if func_ea == int(idaapi.BADADDR) or is_imported_ea(func_ea, self._imported_ea):
            return
        arg_idx = int(getattr(self._objects[0], "index", 0)) if self._objects else 0
        if self._add_visit(func_ea, arg_idx):
            logger.debug(
                "[HexRaysPyTools][Deep Scan Thunk] caller=0x%X -> callee=0x%X arg=%d",
                int(self._cfunc.entry_ea),
                func_ea,
                arg_idx,
            )
            self._add_scan_tree_info(func_ea, arg_idx)

    def _recursive_process(self) -> None:
        """Walk this function, then drain the callee queue recursively."""
        self._maybe_follow_thunk()
        super()._recursive_process()
        while self._new_for_visit:
            func_ea, arg_idx, sub_offset = self._new_for_visit.pop()
            if is_imported_ea(func_ea, self._imported_ea):
                continue
            cfunc = decompile_function(func_ea)
            if cfunc is not None:
                lvars = list(cfunc.get_lvars())
                if arg_idx < 0 or arg_idx >= len(lvars):
                    logger.warning(
                        "Skipping recursive scan at %s: argument %d is outside %d lvars",
                        to_hex(func_ea),
                        arg_idx,
                        len(lvars),
                    )
                    continue
                obj = VariableObject(lvars[arg_idx], arg_idx)
                self.prepare_new_scan(cfunc, arg_idx, obj)
                self._recursive_process()


class RecursiveObjectUpwardsVisitor(RecursiveObjectVisitor, ObjectUpwardsVisitor):
    """Recursive backward visitor: also walk into callers.

    When the tracked object is a function argument, decompile each caller
    and scan it (the call site in the caller becomes the new seed).
    Mirrors the original ``RecursiveObjectUpwardsVisitor``.
    """

    def __init__(
        self,
        cfunc: Any,
        obj: Any,
        data: Any = None,
        skip_after_object: bool = False,
        visited: set[tuple[int, int]] | None = None,
        imported_ea: set[int] | None = None,
    ) -> None:
        super().__init__(cfunc, obj, data, skip_after_object, visited, imported_ea)

    def prepare_new_scan(self, cfunc: Any, arg_idx: int, obj: Any, skip: bool = False) -> None:
        super().prepare_new_scan(cfunc, arg_idx, obj, skip)
        self._call_obj = obj if int(obj.id) == int(SO_CALL_ARGUMENT) else None

    def _check_call(self, cexpr: Any) -> None:
        """If a local arg-var is used, queue all callers for scanning."""
        if int(cexpr.op) != int(idaapi.cot_var):
            return
        lvars = list(self._cfunc.get_lvars())
        idx = int(cexpr.v.idx)
        if idx >= len(lvars):
            return
        is_arg_var = getattr(lvars[idx], "is_arg_var", False)
        if not bool(is_arg_var() if callable(is_arg_var) else is_arg_var):
            return
        func_ea = int(self._cfunc.entry_ea)
        arg_idx = idx
        if self._add_visit(func_ea, arg_idx):
            for callee_ea in get_funcs_calling_address(func_ea):
                self._add_scan_tree_info(callee_ea, arg_idx)

    def _recursive_process(self) -> None:
        """Walk this function, then drain the caller queue recursively."""
        super()._recursive_process()
        while self._new_for_visit:
            new_visit = list(self._new_for_visit)
            self._new_for_visit.clear()
            for func_ea, arg_idx, _sub_offset in new_visit:
                callers = get_funcs_calling_address(func_ea)
                callee_cfunc = decompile_function(func_ea)
                if callee_cfunc is None:
                    continue
                obj = CallArgObject.create(callee_cfunc, arg_idx)
                for callee_ea in callers:
                    cfunc = decompile_function(callee_ea)
                    if cfunc is not None:
                        self.prepare_new_scan(cfunc, arg_idx, obj, False)
                        super()._recursive_process()
