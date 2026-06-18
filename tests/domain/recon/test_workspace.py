"""Test ReconWorkspace skeleton."""
from hexrays_pytools.domain.recon.workspace import ReconWorkspace


def test_workspace_starts_empty() -> None:
    """A new ReconWorkspace has no model."""
    w = ReconWorkspace()
    assert w.is_empty() is True
    assert w.model is None


def test_workspace_clear_keeps_empty() -> None:
    """clear() on an empty workspace is a no-op."""
    w = ReconWorkspace()
    w.clear()
    assert w.is_empty() is True


def test_workspace_instances_are_independent() -> None:
    """Two ReconWorkspaces don't share state."""
    w1 = ReconWorkspace()
    w2 = ReconWorkspace()
    # Mock setting model on w1 should not affect w2
    w1._model = "fake"  # type: ignore[assignment]
    assert w2.is_empty() is True


def test_workspace_can_hold_a_model() -> None:
    """After setting model, is_empty() returns False."""
    w = ReconWorkspace()
    w._model = object()
    assert w.is_empty() is False
    assert w.model is not None


def test_workspace_clear_after_model() -> None:
    """clear() removes the model reference."""
    w = ReconWorkspace()
    w._model = object()
    w.clear()
    assert w.is_empty() is True
    assert w.model is None
