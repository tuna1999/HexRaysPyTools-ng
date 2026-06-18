"""ctree visitor base classes for struct reconstruction.

Extracted from the original `api.py`. Provides ctree_parentee_t subclasses
that traverse a decompiled function and extract struct member candidates.
"""
from __future__ import annotations

from typing import Any

import idaapi  # type: ignore[import-not-found]


class ObjectVisitor(idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Base visitor: walk a cfunc and collect objects matching criteria.

    Subclasses override `_manipulate(cexpr, obj)` to react to expressions.
    The `_objects` list accumulates matched items.
    """
    def __init__(self, cfunc: idaapi.cfunc_t) -> None:
        super().__init__()
        self._cfunc = cfunc
        self._objects: list[Any] = []
        self._init_obj: object | None = None
        self._start_ea: int = 0
        self._skip: bool = False
        self._data: object | None = None

    def process(self) -> None:
        """Run the visitor over the cfunc body."""
        self.apply_to(self._cfunc.body, None)

    @property
    def objects(self) -> list[Any]:
        """The list of objects found during traversal."""
        return list(self._objects)

    def _manipulate(self, cexpr: idaapi.cexpr_t, obj: object) -> None:
        raise NotImplementedError("Subclasses must implement _manipulate")
