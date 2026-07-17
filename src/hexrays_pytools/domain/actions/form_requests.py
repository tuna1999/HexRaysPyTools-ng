"""Form-request actions: open graph, classes, structure builder.

These wire the 3 "show widget" actions to the existing Qt widgets in
``ui/widgets/`` and the graph builder in ``domain/graph/``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from ...domain.graph.structure_graph import StructureGraph
from .action import Action, HexRaysPopupAction

# F1.b: widget classes no longer imported directly. Use session factories
# (session.class_viewer_factory, etc.) wired by plugin.py. The TYPE_CHECKING
# block below imports them for type hints only — not at runtime.

if TYPE_CHECKING:
    from ...ui.widgets.graph_viewer import StructureGraphViewer
    from ..session import Session


class ShowGraph(Action):
    """Open the ctree graph for the current function (BWN_LOCTYPS chooser)."""

    description = "Show graph"
    hotkey = "G"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)
        # Per-instance state — the original stored these on `self`.
        self.graph: StructureGraph | None = None
        self.graph_view: StructureGraphViewer | None = None

    def activate(self, ctx: Any) -> None:
        # Re-show the existing graph if open, otherwise build a new one.
        if self.graph_view is not None:
            try:
                self.graph_view.change_selected([int(sel) + 1 for sel in ctx.chooser_selection])
                self.graph_view.Refresh()
                return
            except (AttributeError, RuntimeError):
                pass
        self.graph = StructureGraph([int(sel) + 1 for sel in ctx.chooser_selection])
        # F1.b: use session factory instead of direct widget import
        if self._session is None or self._session.structure_graph_viewer_factory is None:
            raise RuntimeError("structure_graph_viewer_factory not wired; plugin init incomplete")
        self.graph_view = self._session.structure_graph_viewer_factory(self.graph)
        # IDA 9.x GraphViewer.Show takes a `caption` arg; older IDA didn't.
        if hasattr(self.graph_view, "Show"):
            self.graph_view.Show("Structure Graph")
        else:
            self.graph_view.Refresh()

    def update(self, ctx: Any) -> int:
        if int(ctx.widget_type) == int(idaapi.BWN_LOCTYPS):
            return int(idaapi.AST_ENABLE_FOR_WIDGET)
        return int(idaapi.AST_DISABLE_FOR_WIDGET)


class ShowClasses(Action):
    """Open the Classes (virtual tables) viewer."""

    description = "Classes"
    hotkey = "Alt+F1"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        tform = idaapi.find_widget("Classes")
        if tform:
            idaapi.activate_widget(tform, True)
        else:
            # F1.b: use session factory instead of direct widget import
            if self._session is None or self._session.class_viewer_factory is None:
                raise RuntimeError("class_viewer_factory not wired; plugin init incomplete")
            class_viewer = self._session.class_viewer_factory()
            # IDA 9.x PluginForm.Show takes a `caption` arg.
            if hasattr(class_viewer, "Show"):
                class_viewer.Show("Classes")
            else:
                # Fallback: try anyway (older IDA may accept no args).
                class_viewer.Show()

    def update(self, ctx: Any) -> int:
        return int(idaapi.AST_ENABLE_ALWAYS)


class ShowStructureBuilder(HexRaysPopupAction):
    """Open the Structure Builder widget from the pseudocode popup."""

    description = "Show Structure Builder"
    hotkey = "Alt+F8"
    menu_path = "HexRaysPyTools/Structure/"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        tform = idaapi.find_widget("Structure Builder")
        if tform:
            idaapi.activate_widget(tform, True)
            return
        # F1.b: use session factory instead of direct widget import
        if self._session is None or self._session.structure_builder_factory is None:
            raise RuntimeError("structure_builder_factory not wired; plugin init incomplete")
        builder = self._session.structure_builder_factory(self._session.recon)
        # IDA 9.x PluginForm.Show takes a `caption` arg (older IDA didn't).
        if hasattr(builder, "Show"):
            builder.Show("Structure Builder")
        else:
            builder.Show()

    def check(self, hx_view: Any) -> bool:
        return True
