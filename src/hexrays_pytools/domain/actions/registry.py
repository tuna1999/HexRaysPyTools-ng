"""ActionRegistry — registers all 27 actions with IDA.

Replaces the side-effect import pattern in `callbacks/__init__.py`. All
actions are explicitly listed here; no hidden side effects.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import idaapi  # type: ignore[import-not-found]

if TYPE_CHECKING:
    from ..session import Session
    from .action import Action

logger = logging.getLogger(__name__)


# Explicit list of all 27 action classes. No hidden side effects.
ACTION_CLASSES: tuple = (  # type: ignore[type-arg]
    # Form requests (3)
    "ShowGraph",
    "ShowClasses",
    "ShowStructureBuilder",
    # Function signature (3)
    "ConvertToUsercall",
    "AddRemoveReturn",
    "RemoveArgument",
    # Scanners (5)
    "ShallowScanVariable",
    "DeepScanVariable",
    "RecognizeShape",
    "DeepScanReturn",
    "DeepScanFunctions",
    # Struct (4)
    "FindFieldXrefs",
    "CreateNewField",
    "CreateVtable",
    "GetStructureBySize",
    # Misc (2)
    "GuessAllocation",
    "SwapThenElse",
    # Recast (2)
    "RecastItemLeft",
    "RecastItemRight",
    # Rename (6) — Note: RenameMemberFromFunctionName uses Ctrl+Alt+N (B10 fix)
    "RenameOther",
    "RenameInside",
    "RenameOutside",
    "RenameMemberFromFunctionName",
    "RenameUsingAssert",
    "PropagateName",
    # Containing structure (2)
    "SelectContainingStructure",
    "ResetContainingStructure",
)


class ActionRegistry:
    """Centralized registry with explicit dependency injection."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session
        self._actions: list = []  # type: ignore[type-arg]

    def register_all(self) -> None:
        """Import and register all 27 actions."""
        for action in self._build_actions():
            self._register_one(action)

    def _build_actions(self) -> list:  # type: ignore[type-arg]
        """Lazy-import all action classes. Returns instances."""
        # Lazy imports break circular dependencies. The referenced modules are
        # created in Task 4.5; until then mypy reports [import-untyped]. The
        # ignores become removable once those modules ship a py.typed marker.
        from .containing_structure import (  # type: ignore[import-untyped]
            ResetContainingStructure,
            SelectContainingStructure,
        )
        from .form_requests import (  # type: ignore[import-untyped]
            ShowClasses,
            ShowGraph,
            ShowStructureBuilder,
        )
        from .function_signature import (  # type: ignore[import-untyped]
            AddRemoveReturn,
            ConvertToUsercall,
            RemoveArgument,
        )
        from .guess_allocation import GuessAllocation  # type: ignore[import-untyped]
        from .recast_action import RecastItemLeft, RecastItemRight  # type: ignore[import-untyped]
        from .rename_action import (  # type: ignore[import-untyped]
            PropagateName,
            RenameInside,
            RenameMemberFromFunctionName,
            RenameOther,
            RenameOutside,
            RenameUsingAssert,
        )
        from .scanners import (  # type: ignore[import-untyped]
            DeepScanFunctions,
            DeepScanReturn,
            DeepScanVariable,
            RecognizeShape,
            ShallowScanVariable,
        )
        from .struct_creation import CreateNewField, CreateVtable  # type: ignore[import-untyped]
        from .struct_xref import FindFieldXrefs  # type: ignore[import-untyped]
        from .structs_by_size import GetStructureBySize  # type: ignore[import-untyped]
        from .swap_if_action import SwapThenElse  # type: ignore[import-untyped]
        # All 27 classes in spec order
        all_classes = [
            ShowGraph, ShowClasses, ShowStructureBuilder,
            ConvertToUsercall, AddRemoveReturn, RemoveArgument,
            ShallowScanVariable, DeepScanVariable, RecognizeShape,
            DeepScanReturn, DeepScanFunctions,
            FindFieldXrefs, CreateNewField, CreateVtable, GetStructureBySize,
            GuessAllocation, SwapThenElse,
            RecastItemLeft, RecastItemRight,
            RenameOther, RenameInside, RenameOutside,
            RenameMemberFromFunctionName, RenameUsingAssert, PropagateName,
            SelectContainingStructure, ResetContainingStructure,
        ]
        # Sanity: count matches spec
        if len(all_classes) != 27:
            logger.warning("Expected 27 action classes, found %d", len(all_classes))
        # All classes accept optional session; pass it
        return [cls(self._session) for cls in all_classes]

    def _register_one(self, action: Action) -> None:
        self._actions.append(action)
        idaapi.register_action(
            idaapi.action_desc_t(
                action.name, action.description, action, action.hotkey,
            )
        )
        # Also attach popup actions (lazy import to avoid cycles)
        from .action import HexRaysPopupAction
        if isinstance(action, HexRaysPopupAction):
            # hx_callback manager will attach this; here we just record
            logger.debug("Popup action registered: %s", action.name)

    def unregister_all(self) -> None:
        for action in self._actions:
            idaapi.unregister_action(action.name)
        self._actions = []

    @property
    def actions(self) -> list:  # type: ignore[type-arg]
        return list(self._actions)
