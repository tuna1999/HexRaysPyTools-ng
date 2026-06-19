"""Recast logic — change types of variables/fields/returns to match assignment or cast.

Extracted from `core/helper.py` (recast functions) and `callbacks/recasts.py`.
Real implementation requires full ctree walking; this is the stub skeleton.
"""
from __future__ import annotations

from typing import Any


def recast_item_left(cexpr: Any) -> bool:
    """Recast: var type -> TYPE (left side of assignment)."""
    return False


def recast_item_right(cexpr: Any) -> bool:
    """Recast: var type -> TYPE from (TYPE) cast or function arg type."""
    return False
