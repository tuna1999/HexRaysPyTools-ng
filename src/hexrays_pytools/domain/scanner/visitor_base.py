"""ctree visitor base classes for the struct-reconstruction scanner.

Ported from the original ``api.py:211-405`` (~195 LOC). Provides the
ctree-parentee-t visitor hierarchy that the scanner engine uses to walk a
decompiled function and extract struct member candidates.

Three layers of visitors live here:

* :class:`ObjectVisitor` (base) — owns the tracked-objects list and the
  apply-callback. Subclasses override :meth:`_manipulate` to react to each
  matched expression.
* :class:`ObjectDownwardsVisitor` — *forward* traversal: follows the
  assignment chain downstream (``a = tracked`` ⇒ track ``a`` too).
* :class:`ObjectUpwardsVisitor` — *backward* traversal: builds a
  from→to assignment graph, then re-traverses to find what feeds the
  tracked object.

Recursive variants (cross-function) live in Phase A.4.

All visitors operate on live Hex-Rays ctree objects — this module is not
unit-testable with mocks, so it is excluded from the coverage gate
(``pyproject.toml``).
"""
from __future__ import annotations

import logging
from typing import Any

import idaapi  # type: ignore[import-not-found]

from .scanned_object import SO_RETURNED_OBJECT, ScanObject

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
        self._skip: bool = bool(skip_until_object) if self._start_ea != int(idaapi.BADADDR) else False
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
            int(obj.id), int(cexpr.op),
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

    def __init__(self, cfunc: Any, obj: Any, data: Any = None, skip_until_object: bool = False) -> None:
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

    def __init__(self, cfunc: Any, obj: Any, data: Any = None, skip_after_object: bool = False) -> None:
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
