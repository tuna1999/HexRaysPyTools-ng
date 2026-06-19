"""CONTAINING_RECORD logic — detect/replace negative-offset patterns."""
from __future__ import annotations

from typing import Any


def select_containing_structure(cexpr: Any) -> bool:
    """Prompt user to pick a containing structure + offset, set magic comment."""
    return False


def reset_containing_structure(cexpr: Any) -> bool:
    """Remove the magic comment, reverting to pointer arithmetic."""
    return False
