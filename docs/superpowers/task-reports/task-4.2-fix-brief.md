# Task 4.2 fix: register_all double-instantiation

## Issue

Reviewer caught: `register_all` did `self._register_one(action_cls())` but `_build_actions` already returns instances. Calling an instance of `idaapi.action_handler_t` (which has no `__call__`) raises `TypeError: '...' object is not callable`.

## Fix

Change `register_all` in `src/hexrays_pytools/domain/actions/registry.py`:

```python
def register_all(self) -> None:
    """Import and register all 27 actions."""
    for action in self._build_actions():  # was: action_cls()
        self._register_one(action)
```

## Add regression test

Append to `tests/domain/actions/test_registry.py` (or replace test file):

```python
def test_register_all_does_not_call_instances() -> None:
    """register_all must iterate pre-instantiated actions, not call them as classes."""
    r = ActionRegistry()
    instance1 = MagicMock()
    instance1.name = "action1"
    instance2 = MagicMock()
    instance2.name = "action2"
    r._build_actions = lambda: [instance1, instance2]  # noqa: E731
    r._register_one = MagicMock()
    r.register_all()
    assert r._register_one.call_count == 2
    call_args_list = [call.args[0] for call in r._register_one.call_args_list]
    assert instance1 in call_args_list
    assert instance2 in call_args_list
    instance1.assert_not_called()
    instance2.assert_not_called()
```

## Verification

```bash
PYTHONPATH=src pytest tests/domain/actions/test_registry.py -v
python -m mypy --strict src/hexrays_pytools/domain/actions/registry.py
python -m ruff check src/hexrays_pytools/domain/actions/registry.py tests/domain/actions/test_registry.py
```

## Commit

```bash
git add src/hexrays_pytools/domain/actions/registry.py tests/domain/actions/test_registry.py
git commit -m "fix(actions): register_all was calling instances as classes (TypeError)

Reviewer caught the bug. _build_actions returns instances, but
register_all did self._register_one(action_cls()) which would
TypeError because idaapi.action_handler_t has no __call__.

Co-authored-by: Claude <noreply@anthropic.com>"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-4.2-fix-report.md`
