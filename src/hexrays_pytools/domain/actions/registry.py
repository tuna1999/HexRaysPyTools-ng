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
    from .hx_callback import HxCallbackManager

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
    # Rename (6) — Note: RenameMemberFromFunctionName uses Ctrl+Alt+N
    # (not Ctrl+N) to avoid colliding with RenameOther's hotkey binding.
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

    def __init__(
        self,
        session: Session | None = None,
        hx_callbacks: HxCallbackManager | None = None,
    ) -> None:
        self._session = session
        self._hx_callbacks = hx_callbacks
        self._actions: list = []  # type: ignore[type-arg]

    def register_all(self) -> None:
        """Import and register all 27 actions."""
        for action in self._build_actions():
            self._register_one(action)

    def _build_actions(self) -> list:  # type: ignore[type-arg]
        """Lazy-import all action classes. Returns instances."""
        # Lazy imports break circular dependencies. Task 4.5 created all the
        # referenced action modules; the earlier `# type: ignore[import-untyped]`
        # comments are now removed (the modules exist).
        from .containing_structure import (
            ResetContainingStructure,
            SelectContainingStructure,
        )
        from .form_requests import (
            ShowClasses,
            ShowGraph,
            ShowStructureBuilder,
        )
        from .function_signature import (
            AddRemoveReturn,
            ConvertToUsercall,
            RemoveArgument,
        )
        from .guess_allocation import GuessAllocation
        from .recast_action import RecastItemLeft, RecastItemRight
        from .rename_action import (
            PropagateName,
            RenameInside,
            RenameMemberFromFunctionName,
            RenameOther,
            RenameOutside,
            RenameUsingAssert,
        )
        from .scanners import (
            DeepScanFunctions,
            DeepScanReturn,
            DeepScanVariable,
            RecognizeShape,
            ShallowScanVariable,
        )
        from .struct_creation import CreateNewField, CreateVtable
        from .struct_xref import FindFieldXrefs
        from .structs_by_size import GetStructureBySize
        from .swap_if_action import SwapThenElse

        # All 27 classes in spec order
        all_classes = [
            ShowGraph,
            ShowClasses,
            ShowStructureBuilder,
            ConvertToUsercall,
            AddRemoveReturn,
            RemoveArgument,
            ShallowScanVariable,
            DeepScanVariable,
            RecognizeShape,
            DeepScanReturn,
            DeepScanFunctions,
            FindFieldXrefs,
            CreateNewField,
            CreateVtable,
            GetStructureBySize,
            GuessAllocation,
            SwapThenElse,
            RecastItemLeft,
            RecastItemRight,
            RenameOther,
            RenameInside,
            RenameOutside,
            RenameMemberFromFunctionName,
            RenameUsingAssert,
            PropagateName,
            SelectContainingStructure,
            ResetContainingStructure,
        ]
        # Sanity: count matches spec. Raise to prevent silent count drift —
        # a refactor that forgets to add a class to both ACTION_CLASSES
        # and _build_actions would otherwise ship without CI catching it.
        if len(all_classes) != 27:
            raise RuntimeError(
                f"ActionRegistry: expected 27 action classes, got {len(all_classes)}. "
                "Did you forget to add a class to both ACTION_CLASSES and _build_actions?"
            )
        # All classes accept optional session; pass it
        return [cls(self._session) for cls in all_classes]

    def _register_one(self, action: Action) -> None:
        registered = idaapi.register_action(
            idaapi.action_desc_t(
                action.name,
                action.description,
                action,
                action.hotkey,
            )
        )
        if not registered:
            logger.warning("Failed to register action: %s", action.name)
            return
        self._actions.append(action)
        ida_menu_path = getattr(type(action), "ida_menu_path", None)
        if ida_menu_path is not None and not idaapi.attach_action_to_menu(
            ida_menu_path,
            action.name,
            idaapi.SETMENU_APP,
        ):
            logger.warning("Failed to attach action %s to menu %s", action.name, ida_menu_path)
        # Attach popup actions to the Hex-Rays right-click menu. Each
        # HexRaysPopupAction gets wrapped in a HexRaysPopupRequestHandler
        # registered for hxe_populating_popup; when the user right-clicks in
        # the pseudocode view, Hex-Rays fires that event and the handler calls
        # idaapi.attach_action_to_popup() — that is what makes the action show
        # up in the context menu. Without this, the action is registered
        # (hotkey works) but never appears in the menu.
        from .action import HexRaysPopupAction, HexRaysPopupRequestHandler, HexRaysXrefAction

        if isinstance(action, (HexRaysPopupAction, HexRaysXrefAction)) and self._hx_callbacks is not None:
            self._hx_callbacks.register(
                int(idaapi.hxe_populating_popup),
                HexRaysPopupRequestHandler(action),
            )
            logger.debug("Popup action attached: %s", action.name)

    def unregister_all(self) -> None:
        for action in self._actions:
            ida_menu_path = getattr(type(action), "ida_menu_path", None)
            if ida_menu_path is not None:
                idaapi.detach_action_from_menu(ida_menu_path, action.name)
            idaapi.unregister_action(action.name)
        self._actions = []

    @property
    def actions(self) -> list:  # type: ignore[type-arg]
        return list(self._actions)
