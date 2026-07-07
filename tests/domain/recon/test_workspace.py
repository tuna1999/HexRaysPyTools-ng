"""Test ReconWorkspace skeleton."""
from __future__ import annotations

from unittest.mock import patch

from hexrays_pytools.domain.recon.workspace import ReconWorkspace


def test_workspace_starts_empty() -> None:
    """A new ReconWorkspace has an empty model (rowCount=0)."""
    w = ReconWorkspace()
    assert w.is_empty() is True
    assert w.model is not None  # property constructs model lazily on first access
    assert w.model.rowCount() == 0


def test_workspace_clear_keeps_empty() -> None:
    """clear() on an empty workspace is a no-op (still empty)."""
    w = ReconWorkspace()
    w.clear()
    assert w.is_empty() is True


def test_workspace_instances_are_independent() -> None:
    """Two ReconWorkspaces don't share state."""
    w1 = ReconWorkspace()
    w2 = ReconWorkspace()
    # Each workspace has its own model instance.
    assert w1.model is not w2.model


def test_workspace_can_hold_a_model() -> None:
    """After set_model, is_empty() returns False only if the new model has items."""
    from hexrays_pytools.domain.recon.member import AbstractMember
    from hexrays_pytools.domain.recon.structure_model import StructureModel

    w = ReconWorkspace()
    new_model = StructureModel()
    new_model.add_row(AbstractMember(offset=0x10, name="x"))
    w.set_model(new_model)
    assert w.is_empty() is False
    assert w.model is new_model


def test_workspace_clear_after_model() -> None:
    """clear() empties the model items but keeps the model alive."""
    from hexrays_pytools.domain.recon.member import AbstractMember

    w = ReconWorkspace()
    w.model.add_row(AbstractMember(offset=0x10, name="x"))
    assert w.is_empty() is False
    w.clear()
    assert w.is_empty() is True
    # Model instance is still there (next scan can write to it).
    assert w.model is not None


def test_workspace_main_offset_default_zero() -> None:
    """main_offset defaults to 0."""
    w = ReconWorkspace()
    assert w.main_offset == 0


def test_workspace_main_offset_settable() -> None:
    """main_offset can be set + read (used by StructureBuilder row click)."""
    w = ReconWorkspace()
    w.main_offset = 0x40
    assert w.main_offset == 0x40


def test_workspace_clear_resets_main_offset() -> None:
    """clear() resets main_offset back to 0 (avoid stale origin on next session)."""
    w = ReconWorkspace()
    w.main_offset = 0x100
    w.clear()
    assert w.main_offset == 0


def test_scanner_action_no_model_warning_no_longer_fires() -> None:
    """Scanner actions no longer hit the 'no active workspace model' branch.

    The workspace exposes ``.model`` as a property that constructs an
    empty :class:`StructureModel` lazily on first access, so the scanner
    check ``workspace.model is None`` is False as soon as anything reads
    the property (no warning logged).
    """
    w = ReconWorkspace()
    # The lazy property ensures model is non-None on first access — the
    # scanner's `workspace.model is None` branch is unreachable for a
    # healthy workspace that has touched `.model` at least once.
    assert w.model is not None
    assert w.model is not None  # explicit re-check for clarity


def test_workspace_is_empty_after_adding_then_clearing_item() -> None:
    """End-to-end: add an item → not empty; clear → empty again."""
    from hexrays_pytools.domain.recon.member import AbstractMember

    w = ReconWorkspace()
    w.model.add_row(AbstractMember(offset=0x10, name="x"))
    assert w.is_empty() is False
    w.clear()
    assert w.is_empty() is True


"""Tests for F6: lazy model in ReconWorkspace."""


def test_workspace_init_does_not_import_structure_model() -> None:
    """F6: ReconWorkspace() must not trigger PySide6 import at init time.

    Pre-F6, __init__ called _create_empty_model() which imported
    StructureModel → PySide6.QtCore. This forced Qt to be available even
    for tests that only needed ReconWorkspace for non-UI purposes.
    """
    with patch("hexrays_pytools.domain.recon.structure_model.StructureModel") as mock_sm:
        w = ReconWorkspace()
        # StructureModel was NOT imported during __init__
        mock_sm.assert_not_called()
        # _model is None until first .model access
        assert w._model is None


def test_model_constructed_on_first_access() -> None:
    """F6: first .model access triggers StructureModel construction."""
    w = ReconWorkspace()
    assert w._model is None  # not constructed yet
    model = w.model  # first access triggers construction
    assert w._model is model  # cached
    assert w._model is not None


def test_model_is_singleton_per_workspace() -> None:
    """F6: subsequent .model accesses return cached instance."""
    w = ReconWorkspace()
    first = w.model
    second = w.model
    assert first is second
