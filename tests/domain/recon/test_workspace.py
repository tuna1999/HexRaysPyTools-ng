"""Test ReconWorkspace skeleton."""
from __future__ import annotations

from hexrays_pytools.domain.recon.workspace import ReconWorkspace


def test_workspace_starts_empty() -> None:
    """A new ReconWorkspace has an empty model (rowCount=0)."""
    w = ReconWorkspace()
    assert w.is_empty() is True
    assert w.model is not None  # always pre-created now
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

    Pre-create model in __init__ was the fix — the workspace always has
    a model, so the scanner check ``workspace.model is None`` is False
    from the start (no warning logged).
    """
    w = ReconWorkspace()
    # The pre-create ensures model is non-None — the scanner's
    # `workspace.model is None` branch is unreachable for a healthy workspace.
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
