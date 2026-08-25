"""Scanner actions: shallow/deep scan, recognize shape, scan returns and functions.

These wire the 5 scanner actions to the :class:`SearchVisitor` engine
(Phase A.5). The visitor's ctree walk is verified end-to-end in real IDA
via idat headless; these tests cover the Python-level wiring (object
construction, dispatch by citype, etc.).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from ...domain.recon.structure_model import StructureModel
from ...domain.recon.workspace import ReconWorkspace
from ...domain.scanner.helpers import FunctionTouchVisitor
from ...domain.scanner.member_extractor import (
    DeepReturnVisitor,
    NewDeepSearchVisitor,
    NewShallowSearchVisitor,
)
from ...domain.scanner.scanned_object import (
    SO_LOCAL_VARIABLE,
    ReturnedObject,
    ScanObject,
    VariableObject,
)
from ...domain.types.tinfo_utils import is_legal_type
from .action import Action, HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session

logger = logging.getLogger(__name__)


class Scanner(HexRaysPopupAction):
    """Abstract scanner. Concrete subclasses implement ``activate``.

    All concrete scanners share the same ``check`` predicate: the
    ctree_item under the cursor must resolve to a :class:`ScanObject`
    via :meth:`ScanObject.create` AND its tinfo must be legal. Subclasses
    override ``activate``.
    """

    description = "Scan"
    hotkey: str | None = None
    menu_path = "HexRaysPyTools/Scan/"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def _can_be_scanned(self, cfunc: Any, ctree_item: Any) -> bool:
        """Return True if the ctree_item is a scan target with a legal tinfo."""
        obj = ScanObject.create(cfunc, ctree_item)
        if obj is None:
            return False
        if obj.tinfo is None:
            return False
        return bool(is_legal_type(obj.tinfo))

    def check(self, hx_view: Any) -> bool:
        cfunc, ctree_item = hx_view.cfunc, hx_view.item
        return self._can_be_scanned(cfunc, ctree_item)

    def _workspace(self) -> Any:
        """Return the ReconWorkspace, or None if no session."""
        if self._session is None or self._session.recon is None:
            return None
        return self._session.recon

    def _consts(self) -> Any:
        """Return the session's Consts dataclass, or None if no session."""
        if self._session is None:
            return None
        return self._session.consts

    @staticmethod
    def _output(message: str) -> None:
        """Emit scanner diagnostics at DEBUG level."""
        logger.debug("%s", message)

    @staticmethod
    def _log_scan_start(kind: str, cfunc: Any, obj: Any, origin: int) -> None:
        """Emit a scan-start marker at DEBUG level."""
        func_ea = int(getattr(cfunc, "entry_ea", 0))
        func_name = str(idaapi.get_name(func_ea) or f"sub_{func_ea:X}")
        obj_name = str(getattr(obj, "name", "<unknown>"))
        message = (
            f"[HexRaysPyTools][{kind}] {obj_name} in {func_name} "
            f"@ 0x{func_ea:X} (origin=0x{int(origin):X})"
        )
        Scanner._output(message)


class ShallowScanVariable(Scanner):
    """Scan the selected variable once, depth-limited."""

    description = "Scan Variable"
    hotkey = "F"

    def activate(self, ctx: Any) -> None:
        self._output("[HexRaysPyTools][Scan] action invoked")
        hx_view = idaapi.get_widget_vdui(ctx.widget)
        if hx_view is None:
            self._output("[HexRaysPyTools][Scan] skipped: pseudocode view is unavailable")
            return
        cfunc = hx_view.cfunc
        workspace = self._workspace()
        if workspace is None:
            self._output("[HexRaysPyTools][Scan] skipped: no active reconstruction workspace")
            return
        if not self._can_be_scanned(cfunc, hx_view.item):
            self._output("[HexRaysPyTools][Scan] skipped: selected item is not a scannable typed object")
            return
        obj = ScanObject.create(cfunc, hx_view.item)
        if obj is None:
            self._output("[HexRaysPyTools][Scan] skipped: failed to create scan object")
            return
        self._log_scan_start("Scan", cfunc, obj, int(workspace.main_offset))
        visitor = NewShallowSearchVisitor(
            cfunc, int(workspace.main_offset), obj, workspace, consts=self._consts()
        )
        visitor.process()


class DeepScanVariable(Scanner):
    """Recursively scan the selected variable (also walks callees)."""

    description = "Deep Scan Variable"
    hotkey = "Shift+Alt+F"

    def activate(self, ctx: Any) -> None:
        self._output("[HexRaysPyTools][Deep Scan] action invoked")
        hx_view = idaapi.get_widget_vdui(ctx.widget)
        if hx_view is None:
            self._output("[HexRaysPyTools][Deep Scan] skipped: pseudocode view is unavailable")
            return
        cfunc = hx_view.cfunc
        workspace = self._workspace()
        if workspace is None:
            self._output("[HexRaysPyTools][Deep Scan] skipped: no active reconstruction workspace")
            return
        if not self._can_be_scanned(cfunc, hx_view.item):
            self._output(
                "[HexRaysPyTools][Deep Scan] skipped: selected item is not a scannable typed object"
            )
            return
        # Capture the selected object before touching/decompiling callees.
        # FunctionTouchVisitor can cause Hex-Rays to rebuild the current ctree,
        # making hx_view.item stale. The upstream plugin follows this ordering
        # for the same reason: create obj first, then pre-touch callees.
        obj = ScanObject.create(cfunc, hx_view.item)
        if obj is None:
            self._output("[HexRaysPyTools][Deep Scan] skipped: failed to create scan object")
            return
        # Pre-decompile all callees so their arg types are known before the
        # recursive scan starts. FunctionTouchVisitor is best-effort — if it
        # fails, the deep scan still runs.
        imported_ea = self._session.imported_ea if self._session is not None else set()
        touched = self._session.touched_functions if self._session is not None else set()
        if FunctionTouchVisitor(cfunc, touched, imported_ea).process():
            hx_view.refresh_view(True)
        current_cfunc = hx_view.cfunc
        self._log_scan_start("Deep Scan", current_cfunc, obj, int(workspace.main_offset))
        visitor = NewDeepSearchVisitor(
            current_cfunc, int(workspace.main_offset), obj, workspace, consts=self._consts()
        )
        visitor.process()


class RecognizeShape(Scanner):
    """Attempt to recognize the shape of the selected expression.

    Runs a shallow scan into a *fresh* model (the user's current model
    may have unrelated entries), builds a UDT tinfo from the discovered
    members, and applies the type to the scanned lvar/global.
    """

    description = "Recognize Shape"

    def activate(self, ctx: Any) -> None:
        hx_view = idaapi.get_widget_vdui(ctx.widget)
        if hx_view is None:
            return
        cfunc = hx_view.cfunc
        if not self._can_be_scanned(cfunc, hx_view.item):
            return
        obj = ScanObject.create(cfunc, hx_view.item)
        if obj is None:
            return

        # Fresh model — the recognized shape comes from THIS scan, not
        # the user's existing accumulation.
        fresh_workspace = ReconWorkspace()
        fresh_workspace.set_model(StructureModel())
        # origin=0 for RecognizeShape — the recognized shape starts at
        # the scanned offset, not the user's main_offset.
        visitor = NewShallowSearchVisitor(cfunc, 0, obj, fresh_workspace, consts=self._consts())
        visitor.process()
        assert fresh_workspace.model is not None
        tinfo = fresh_workspace.model.get_recognized_shape()
        if tinfo is None:
            return
        # Original: apply as a pointer (the recognized shape is the
        # pointee, the var is a `type*`).
        tinfo.create_ptr(tinfo)
        if int(obj.id) == int(SO_LOCAL_VARIABLE):
            # Local variable
            assert isinstance(obj, VariableObject)
            hx_view.set_lvar_type(obj.lvar, tinfo)
        elif int(obj.id) == int(idaapi.cot_obj):
            # cot_obj — global
            idaapi.apply_tinfo(int(obj.ea), tinfo, idaapi.TINFO_DEFINITE)
        hx_view.refresh_view(True)


class DeepScanReturn(Scanner):
    """Scan variables returned by the current function.

    Uses :class:`DeepReturnVisitor` with a :class:`ReturnedObject` seed.
    Restricts activation to ctree_item.citype == VDI_FUNC (must be the
    function itself, not a child expression).
    """

    description = "Deep Scan Returned Variables"

    def check(self, hx_view: Any) -> bool:
        cfunc, ctree_item = hx_view.cfunc, hx_view.item
        if int(ctree_item.citype) != int(idaapi.VDI_FUNC):
            return False
        func_tinfo = idaapi.tinfo_t()
        cfunc.get_func_type(func_tinfo)
        return bool(is_legal_type(func_tinfo.get_rettype()))

    def activate(self, ctx: Any) -> None:
        hx_view = idaapi.get_widget_vdui(ctx.widget)
        if hx_view is None:
            return
        cfunc = hx_view.cfunc
        workspace = self._workspace()
        if workspace is None:
            logger.warning("DeepScanReturn: no active session — skipping")
            return
        obj = ReturnedObject(int(cfunc.entry_ea))
        visitor = DeepReturnVisitor(
            cfunc, int(workspace.main_offset), obj, workspace, consts=self._consts()
        )
        visitor.process()


class DeepScanFunctions(Action):
    """Scan the first argument across all selected functions.

    Operates on the BWN_FUNCS chooser (``ctx.chooser_selection``), NOT
    on a pseudocode widget — hence the inheritance from :class:`Action`
    (not :class:`HexRaysPopupAction`).
    """

    description = "Scan First Argument"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def update(self, ctx: Any) -> int:
        if int(ctx.widget_type) == int(idaapi.BWN_FUNCS):
            return int(idaapi.AST_ENABLE_FOR_WIDGET)
        return int(idaapi.AST_DISABLE_FOR_WIDGET)

    def activate(self, ctx: Any) -> None:
        workspace = (
            self._session.recon
            if self._session is not None and self._session.recon is not None
            else None
        )
        if workspace is None:
            logger.warning("DeepScanFunctions: no active session — skipping")
            return
        consts = self._session.consts if self._session is not None else None
        for idx in ctx.chooser_selection:
            try:
                func_ea = int(idaapi.getn_func(int(idx) - 1).start_ea)
            except (AttributeError, TypeError):
                continue
            # Decompile the target function — import decompile_function lazily
            # to avoid an import cycle with helpers.py.
            from ...domain.scanner.helpers import decompile_function

            cfunc = decompile_function(func_ea)
            if cfunc is None:
                continue
            lvars = list(cfunc.get_lvars())
            if not lvars:
                continue
            obj = VariableObject(lvars[0], 0)
            NewDeepSearchVisitor(cfunc, 0, obj, workspace, consts=consts).process()
