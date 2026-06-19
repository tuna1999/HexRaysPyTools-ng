"""Scanner helpers: decompilation wrapper + function-touch visitor.

Ported from the original ``core/helper.py:291-397``. These power the deep
scanner (Phase A.5) and the scanner actions (Phase B.7):

* :func:`decompile_function` — wraps :func:`idaapi.decompile` with a
  ``DecompilationFailure`` guard so a bad function doesn't abort the whole
  deep scan.
* :class:`FunctionTouchVisitor` — pre-decompiles all callees of a function
  so Hex-Rays has parsed their argument types before the deep scanner
  needs them. Without this, the scanner sees placeholder arg types and
  misses member candidates. Used by the ``DeepScanVariable`` action.

Everything here operates on live Hex-Rays ctree objects, so this module is
not unit-testable end-to-end with mocks — only the Python-level control
flow (the exception guard, the set membership) is covered by tests.
"""
from __future__ import annotations

import logging
from typing import Any

import idaapi  # type: ignore[import-not-found]

from ...infra.arch.arch import is_imported_ea

logger = logging.getLogger(__name__)


def decompile_function(address: int) -> Any:
    """Decompile the function at ``address``; return cfunc or None.

    Mirrors the original ``helper.decompile_function``. Catches
    ``DecompilationFailure`` (Hex-Rays could not decompile — e.g. the
    function is too complex or the call target is a thunk) and returns
    ``None`` instead of propagating the exception, so the deep scanner can
    skip the function and continue.
    """
    try:
        cfunc = idaapi.decompile(address)
        if cfunc:
            return cfunc
    except idaapi.DecompilationFailure:
        pass
    logger.warning("IDA failed to decompile function at 0x%08X", int(address))
    return None


class FunctionTouchVisitor(idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Pre-decompile all callees of a function so their arg types are known.

    Hex-Rays lazily parses a function's argument types the first time you
    decompile it. The deep scanner reads callee arg types during the
    scan — if the callee hasn't been decompiled yet, the arg types come
    back as generic ``__int64`` and the scanner misses struct member
    candidates. Walking the call graph first and forcing a decompile on
    each callee primes the cache.

    Mirrors the original ``helper.FunctionTouchVisitor`` (``helper.py:291``).
    """

    def __init__(self, cfunc: Any, touched: set[int], imported_ea: set[int]) -> None:
        super().__init__()
        self.cfunc = cfunc
        self.functions: set[int] = set()
        # Session-owned caches, passed in by the caller (replaces the
        # original module globals cache.touched_functions / cache.imported_ea).
        self._touched = touched
        self._imported_ea = imported_ea

    def visit_expr(self, expression: Any) -> int:
        if int(expression.op) == int(idaapi.cot_call):
            self.functions.add(int(expression.x.obj_ea))
        return 0

    def touch_all(self) -> None:
        """Decompile every as-yet-untouched callee in ``self.functions``."""
        diff = self.functions.difference(self._touched)
        for address in diff:
            if is_imported_ea(address, self._imported_ea):
                continue
            try:
                cfunc = idaapi.decompile(address)
                if cfunc:
                    FunctionTouchVisitor(cfunc, self._touched, self._imported_ea).process()
            except idaapi.DecompilationFailure:
                logger.warning("IDA failed to decompile function at 0x%08X", address)
                self._touched.add(address)
        idaapi.decompile(int(self.cfunc.entry_ea))

    def process(self) -> bool:
        """Process this function: mark touched, walk, touch_all. Returns True if new."""
        if int(self.cfunc.entry_ea) not in self._touched:
            self._touched.add(int(self.cfunc.entry_ea))
            self.apply_to(self.cfunc.body, None)
            self.touch_all()
            return True
        return False
