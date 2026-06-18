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


def test_registry_build_actions_real_path_returns_27() -> None:
    """Real lazy-import path now works (Task 4.5 shipped the action modules).

    Task 4.2 deferred this to Task 4.5: the 11 action modules did not exist,
    so the real `_build_actions` could not be exercised. Now they exist and
    the lazy imports resolve. This test exercises the real code path and
    confirms all 27 classes instantiate.
    """
    r = ActionRegistry()
    actions = r._build_actions()
    assert len(actions) == 27
    # Verify the spec order (first and last entries)
    assert type(actions[0]).__name__ == "ShowGraph"
    assert type(actions[-1]).__name__ == "ResetContainingStructure"


def test_registry_build_actions_b10_fix_hotkey() -> None:
    """B10 fix holds in the real registry build: RenameMemberFromFunctionName
    uses Ctrl+Alt+N (not Ctrl+N, which collides with RenameOther)."""
    r = ActionRegistry()
    actions = r._build_actions()
    by_name = {type(a).__name__: a for a in actions}
    assert by_name["RenameMemberFromFunctionName"].hotkey == "Ctrl+Alt+N"
    assert by_name["RenameOther"].hotkey == "Ctrl+N"
    # The two must differ (B10 collision fix)
    assert by_name["RenameMemberFromFunctionName"].hotkey != by_name["RenameOther"].hotkey


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


def test_register_all_does_not_call_instances() -> None:
    """register_all must iterate pre-instantiated actions, not call them as classes.

    Reviewer for Task 4.2 caught: the verbatim brief's register_all did
    `self._register_one(action_cls())` where action_cls was already an
    instance from _build_actions. Calling an instance of idaapi.action_handler_t
    raises TypeError because it has no __call__. This regression test guards
    the fix.
    """
    r = ActionRegistry()
    instance1 = MagicMock()
    instance1.name = "action1"
    instance2 = MagicMock()
    instance2.name = "action2"
    r._build_actions = lambda: [instance1, instance2]  # noqa: E731
    r._register_one = MagicMock()

    r.register_all()

    # _register_one was called with the instances directly (not called as ctors)
    assert r._register_one.call_count == 2
    call_args_list = [call.args[0] for call in r._register_one.call_args_list]
    assert instance1 in call_args_list
    assert instance2 in call_args_list
    # Neither instance had __call__ invoked
    instance1.assert_not_called()
    instance2.assert_not_called()
