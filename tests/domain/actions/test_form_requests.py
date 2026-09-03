"""Test form_requests actions (ShowGraph, ShowClasses, ShowStructureBuilder)."""
from unittest.mock import MagicMock, patch

from hexrays_pytools.domain.actions.action import Action, HexRaysPopupAction
from hexrays_pytools.domain.actions.form_requests import (
    ShowClasses,
    ShowGraph,
    ShowStructureBuilder,
)


def test_show_graph_is_action() -> None:
    assert issubclass(ShowGraph, Action)


def test_show_graph_description_and_hotkey() -> None:
    assert ShowGraph.description == "Show graph"
    assert ShowGraph.hotkey == "G"


def test_show_graph_instantiable_and_activates() -> None:
    session = MagicMock()
    session.structure_graph_viewer_factory = MagicMock(return_value=MagicMock())
    a = ShowGraph(session=session)
    assert a.name == "HexRaysPyTools:ShowGraph"
    ctx = MagicMock()
    ctx.chooser_selection = [0]
    a.activate(ctx)  # should not raise


def test_show_graph_accepts_session() -> None:
    session = MagicMock()
    a = ShowGraph(session=session)
    assert a._session is session


def test_show_classes_is_action() -> None:
    assert issubclass(ShowClasses, Action)
    assert ShowClasses.description == "Classes"
    assert ShowClasses.hotkey == "Alt+F1"
    assert ShowClasses.ida_menu_path == "View/Open subviews/Local types"


def test_show_classes_instantiable_and_activates() -> None:
    session = MagicMock()
    session.class_viewer_factory = MagicMock(return_value=MagicMock())
    a = ShowClasses(session=session)
    assert a.name == "HexRaysPyTools:ShowClasses"
    a.activate(MagicMock())


def test_show_structure_builder_is_popup_action() -> None:
    assert issubclass(ShowStructureBuilder, HexRaysPopupAction)
    assert ShowStructureBuilder.description == "Show Structure Builder"
    assert ShowStructureBuilder.hotkey == "Alt+F8"


def test_show_structure_builder_check_returns_true() -> None:
    session = MagicMock()
    session.structure_builder_factory = MagicMock(return_value=MagicMock())
    session.recon = MagicMock()
    a = ShowStructureBuilder(session=session)
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())  # should not raise


# ---------------------------------------------------------------------------
# F1.b: widget factory wiring via Session
# ---------------------------------------------------------------------------


def test_session_has_widget_factory_fields() -> None:
    """F1.b: Session must expose 3 widget factory fields."""
    from hexrays_pytools.domain.session import Session

    s = Session()
    assert hasattr(s, "class_viewer_factory")
    assert hasattr(s, "structure_graph_viewer_factory")
    assert hasattr(s, "structure_builder_factory")
    # Default None — plugin entry wires them after construction
    assert s.class_viewer_factory is None
    assert s.structure_graph_viewer_factory is None
    assert s.structure_builder_factory is None


def test_form_requests_uses_factory_not_direct_import() -> None:
    """F1.b: form_requests.py must NOT directly import widget classes at runtime.

    Imports are allowed inside ``TYPE_CHECKING`` for type hints — but not as
    top-level runtime imports, which would re-introduce the domain→ui
    upward dependency the F1.b fix removed.
    """
    import ast
    import inspect

    from hexrays_pytools.domain.actions import form_requests

    tree = ast.parse(inspect.getsource(form_requests))
    runtime_imports: list[str] = []
    for node in tree.body:
        # Top-level runtime imports only (skip ast.If blocks — those
        # are TYPE_CHECKING-guarded and only run under mypy/pyright).
        if (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.startswith("...ui.widgets")
        ):
            names = ", ".join(n.name for n in node.names)
            runtime_imports.append(f"from {node.module} import {names}")
    assert runtime_imports == [], (
        "form_requests.py has runtime imports of UI widgets: "
        f"{runtime_imports}. Use session factories instead."
    )


def test_show_classes_calls_class_viewer_factory() -> None:
    """ShowClasses.activate uses session.class_viewer_factory."""
    from hexrays_pytools.domain.actions.form_requests import ShowClasses

    mock_factory = MagicMock(return_value=MagicMock())
    session = MagicMock()
    session.class_viewer_factory = mock_factory
    a = ShowClasses(session=session)
    with patch("hexrays_pytools.domain.actions.form_requests.idaapi.find_widget", return_value=None):
        a.activate(MagicMock())
    mock_factory.assert_called_once()


def test_show_structure_builder_calls_factory() -> None:
    """ShowStructureBuilder.activate uses session.structure_builder_factory."""
    from hexrays_pytools.domain.actions.form_requests import ShowStructureBuilder

    mock_factory = MagicMock(return_value=MagicMock())
    session = MagicMock()
    session.recon = MagicMock()
    session.structure_builder_factory = mock_factory
    a = ShowStructureBuilder(session=session)
    with patch("hexrays_pytools.domain.actions.form_requests.idaapi.find_widget", return_value=None):
        a.activate(MagicMock())
    mock_factory.assert_called_once()


def test_show_graph_uses_factory() -> None:
    """ShowGraph.activate uses session.structure_graph_viewer_factory."""
    from hexrays_pytools.domain.actions.form_requests import ShowGraph

    mock_factory = MagicMock(return_value=MagicMock())
    session = MagicMock()
    session.structure_graph_viewer_factory = mock_factory
    a = ShowGraph(session=session)
    # Need a ctx with chooser_selection attribute
    ctx = MagicMock()
    ctx.chooser_selection = [0]
    a.activate(ctx)
    mock_factory.assert_called_once()


def test_show_classes_raises_when_factory_not_wired() -> None:
    """ShowClasses raises RuntimeError if class_viewer_factory is None."""
    import pytest

    from hexrays_pytools.domain.actions.form_requests import ShowClasses

    session = MagicMock()
    session.class_viewer_factory = None
    a = ShowClasses(session=session)
    # Mock idaapi.find_widget to return None so we exercise the factory branch
    with (
        patch("hexrays_pytools.domain.actions.form_requests.idaapi.find_widget", return_value=None),
        pytest.raises(RuntimeError, match="class_viewer_factory not wired"),
    ):
        a.activate(MagicMock())


def test_show_graph_update_attaches_to_loctyps_popup() -> None:
    """In the Local Types chooser, ShowGraph must attach itself to the popup."""
    import idaapi  # type: ignore[import-not-found]

    a = ShowGraph()
    ctx = MagicMock()
    with patch.object(idaapi, "BWN_LOCTYPS", 41), patch.object(
        idaapi, "AST_ENABLE_FOR_WIDGET", 1
    ), patch.object(idaapi, "attach_action_to_popup") as attach:
        ctx.widget_type = 41
        result = a.update(ctx)
    assert result == 1
    attach.assert_called_once_with(ctx.widget, None, a.name)


def test_show_graph_recreates_viewer_after_window_closed() -> None:
    """A closed graph window (GetWidget() -> None) must not block reopening."""
    session = MagicMock()
    factory = MagicMock(side_effect=lambda graph: MagicMock())
    session.structure_graph_viewer_factory = factory
    a = ShowGraph(session=session)
    # First open — factory called once.
    ctx = MagicMock()
    ctx.chooser_selection = [0]
    a.activate(ctx)
    assert factory.call_count == 1
    # Simulate the user closing the window: viewer alive but widget gone.
    closed_viewer = a.graph_view
    closed_viewer.GetWidget.return_value = None
    a.activate(ctx)
    assert factory.call_count == 2
    assert a.graph_view is not closed_viewer


def test_show_graph_reuses_live_viewer() -> None:
    """An open graph window is reused (no new factory call)."""
    session = MagicMock()
    factory = MagicMock(side_effect=lambda graph: MagicMock())
    session.structure_graph_viewer_factory = factory
    a = ShowGraph(session=session)
    ctx = MagicMock()
    ctx.chooser_selection = [0]
    a.activate(ctx)
    a.graph_view.GetWidget.return_value = MagicMock()  # window still open
    a.activate(ctx)
    assert factory.call_count == 1
    a.graph_view.change_selected.assert_called_once_with([1])
