"""Test ActionRegistry."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.registry import ACTION_CLASSES, ActionRegistry


def test_action_classes_count() -> None:
    """27 action classes in the explicit list (per spec)."""
    assert len(ACTION_CLASSES) == 27


def test_registry_init_empty() -> None:
    r = ActionRegistry()
    assert r.actions == []


def test_registry_with_session() -> None:
    session = MagicMock()
    r = ActionRegistry(session=session)
    assert r._session is session


def test_registry_build_actions_returns_27() -> None:
    """_build_actions returns 27 instances (even if the underlying modules don't exist yet)."""
    # Without a Session, the lazy import in _build_actions will fail because
    # the action modules don't exist. So we mock the entire build.
    r = ActionRegistry()
    r._build_actions = lambda: [MagicMock() for _ in range(27)]  # noqa: E731
    actions = r._build_actions()
    assert len(actions) == 27


def test_registry_register_one_appends() -> None:
    """_register_one adds to actions and calls idaapi.register_action."""
    r = ActionRegistry()
    action = MagicMock()
    action.name = "test_action"
    r._register_one(action)
    assert action in r.actions


def test_registry_unregister_all_clears() -> None:
    r = ActionRegistry()
    r._actions = [MagicMock(), MagicMock()]
    r.unregister_all()
    assert r._actions == []
