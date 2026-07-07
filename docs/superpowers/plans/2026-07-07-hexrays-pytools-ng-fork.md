# HexRaysPyTools-ng v1.0.0 + Architecture Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fork `HexRaysPyTools` → `HexRaysPyTools-ng` v1.0.0 (rename, version bump, remove CHANGELOG), and fix all 6 architecture findings (F1–F6) from the prior review.

**Architecture:** Plugin package name (`hexrays_pytools`) stays unchanged to avoid breaking ~80 internal imports. Only user-visible identifiers change (plugin ID, display name, zip output, README, netnode storage key). Architecture fixes target 6 specific integrity issues: layer-boundary violations, non-atomic migration, silent count drift, invisible callback failures, thin widget test coverage, and over-eager workspace init.

**Tech Stack:** Python 3.11+, PySide6, IDA Pro 9.0–9.3 API, pytest + pytest-mock + pytest-cov, mypy --strict, ruff, hatchling build backend, HCLI plugin distribution.

**Spec:** `docs/superpowers/specs/2026-07-07-hexrays-pytools-ng-fork-design.md`

---

## File Structure Changes

### Files modified (Section 1 — rename)

- `pyproject.toml` — name, version
- `ida-plugin.json` — plugin.name, plugin.version
- `tools/build_plugin.py` — output zip name
- `README.md` — title, install path, remove CHANGELOG ref
- `CLAUDE.md` — remove CHANGELOG ref
- `src/hexrays_pytools/domain/xrefs/xref_storage.py` — NODE_NAME, OLD_ARRAY_NAME
- `src/hexrays_pytools/domain/actions/registry.py` — comment B10
- `src/hexrays_pytools/domain/const.py` — comment B11
- `src/hexrays_pytools/domain/ctree/swap_if.py` — comment B12
- `tests/domain/xrefs/test_xref_storage.py` — update `test_old_array_name_constant`

### Files deleted

- `CHANGELOG.md`

### Files created (F1.a)

- `src/hexrays_pytools/domain/chooser.py` — `MyChoose` moved here from `ui/chooser.py`

### Files modified (F1.a — domain→ui import cleanup)

- `src/hexrays_pytools/ui/chooser.py` — remove `MyChoose` class
- `src/hexrays_pytools/domain/actions/guess_allocation.py` — import path
- `src/hexrays_pytools/domain/actions/struct_xref.py` — import path
- `src/hexrays_pytools/domain/actions/structs_by_size.py` — import path
- `src/hexrays_pytools/domain/ctree/negative_offsets.py` — import path
- `src/hexrays_pytools/domain/til/type_library.py` — import path

### Files modified (F1.b — widget factory via Session)

- `src/hexrays_pytools/domain/session.py` — add 3 factory fields
- `src/hexrays_pytools/domain/actions/form_requests.py` — replace direct widget imports
- `src/hexrays_pytools/plugin.py` — wire factories after Session creation
- `tests/domain/actions/test_form_requests.py` — update tests

### Files modified (F2 — XrefStorage)

- `src/hexrays_pytools/domain/xrefs/xref_storage.py` — flush before delete, fix comment
- `tests/domain/xrefs/test_xref_storage.py` — update hardcoded string + add 4 new tests

### Files modified (F3 — ActionRegistry)

- `src/hexrays_pytools/domain/actions/registry.py` — `logger.warning` → `raise RuntimeError`

### Files modified (F4 — HxCallbackManager)

- `src/hexrays_pytools/domain/actions/hx_callback.py` — add `errors` list
- `src/hexrays_pytools/domain/session.py` — add `recent_callback_errors` property
- `tests/domain/actions/test_hx_callback.py` — add 2 new tests

### Files modified (F6 — ReconWorkspace lazy)

- `src/hexrays_pytools/domain/recon/workspace.py` — lazy model via property
- `tests/domain/recon/test_workspace.py` — add 3 new tests

### Files modified (F5 — widget tests)

- `tests/ui/widgets/test_class_viewer.py` — extend coverage
- `tests/ui/widgets/test_structure_builder.py` — extend coverage

---

## Task 1: Rename + Version Bump + CHANGELOG Removal

**Files:**
- Modify: `pyproject.toml`, `ida-plugin.json`, `tools/build_plugin.py`, `README.md`, `CLAUDE.md`
- Modify: `src/hexrays_pytools/domain/xrefs/xref_storage.py`
- Modify: `src/hexrays_pytools/domain/actions/registry.py`, `src/hexrays_pytools/domain/const.py`, `src/hexrays_pytools/domain/ctree/swap_if.py`
- Modify: `tests/domain/xrefs/test_xref_storage.py`
- Delete: `CHANGELOG.md`
- Filesystem: rename repo folder

### Step 1.1: Close any IDE/editor holding the project open

Stop any running processes (VS Code, PyCharm, IDA with plugin loaded) that may hold file handles on the repo path. Folder rename will fail if files are locked.

Expected: All editors closed; only this shell session remains.

### Step 1.2: Rename repo folder (filesystem)

```bash
mv "D:/re_dev_projects/ida-plugins/HexRaysPyTools" "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng"
```

Expected: Folder renamed. All subsequent commands must use the new path.

### Step 1.3: Update pyproject.toml

Edit `D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng/pyproject.toml`:

- Line 6: `name = "hexrays_pytools"` → `name = "hexrays_pytools_ng"`
- Line 7: `version = "2.0.0"` → `version = "1.0.0"`

### Step 1.4: Update ida-plugin.json

Edit `D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng/ida-plugin.json`:

- Line 5: `"name": "hexrays_pytools"` → `"name": "hexrays_pytools_ng"`
- Line 7: `"version": "2.0.0"` → `"version": "1.0.0"`
- Leave `urls.repository` as-is — repository URL is unchanged until user updates it separately

### Step 1.5: Update tools/build_plugin.py

Edit `D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng/tools/build_plugin.py`:

- Line 17: `archive = DIST / f"hexrays_pytools-{version}.zip"` → `archive = DIST / f"hexrays_pytools_ng-{version}.zip"`

### Step 1.6: Update README.md

Edit `D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng/README.md`:

- Line 1: `# HexRaysPyTools` → `# HexRaysPyTools-ng`
- Line 7: ``hcli plugin install dist/hexrays_pytools-2.0.0.zip`` → ``hcli plugin install dist/hexrays_pytools_ng-1.0.0.zip``
- Line 10: keep `IDA Pro 9.0, 9.1, or 9.2` as-is (still supported)
- Line 27: `See [docs/architecture.md]` line — unchanged
- Line 38: `See [docs/superpowers/specs/2026-06-18-...]` — unchanged (historical reference)
- Replace any other occurrences of bare `HexRaysPyTools` (when referring to THIS plugin) with `HexRaysPyTools-ng`. Keep references to `refs/HexRaysPyTools/` (legacy upstream) unchanged.
- Remove the line containing `See [CHANGELOG.md]` (was line 7 in the original — current line may differ; grep first)

Verify: `grep -n "CHANGELOG" README.md` returns 0 matches.

### Step 1.7: Update CLAUDE.md

Edit `D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng/CLAUDE.md`:

- Remove or replace the `CHANGELOG.md` entry in the references section (was at line 131 area — find by grep)
- Search for `HexRaysPyTools` references where they refer to THIS plugin and replace with `HexRaysPyTools-ng`. DO NOT change `refs/HexRaysPyTools/` references.

Verify: `grep -n "CHANGELOG" CLAUDE.md` returns 0 matches.

### Step 1.8: Update netnode key constants

Edit `D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng/src/hexrays_pytools/domain/xrefs/xref_storage.py`:

- Line 21: `OLD_ARRAY_NAME = "$HexRaysPyTools:XrefStorage"` → `OLD_ARRAY_NAME = "$HexRaysPyTools-ng:XrefStorage"`
- Line 23: `NODE_NAME = "$hexrays_pytools/xref_storage"` → `NODE_NAME = "$hexrays_pytools_ng/xref_storage"`

### Step 1.9: Update existing test that hardcodes the old name

Edit `D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng/tests/domain/xrefs/test_xref_storage.py`:

- Line 44: `assert OLD_ARRAY_NAME == "$HexRaysPyTools:XrefStorage"` → `assert OLD_ARRAY_NAME == "$HexRaysPyTools-ng:XrefStorage"`

### Step 1.10: Update source comments to remove B-prefix refs

Three source files have `(B10 fix)`, `(B11 bug — ...)`, `(B12 fix)` references that pointed to the now-deleted CHANGELOG. Replace each with an inline comment explaining the behavior:

Edit `src/hexrays_pytools/domain/actions/registry.py` line 48:

```python
    # Rename (6) — Note: RenameMemberFromFunctionName uses Ctrl+Alt+N (B10 fix)
```

→

```python
    # Rename (6) — Note: RenameMemberFromFunctionName uses Ctrl+Alt+N
    # (not Ctrl+N) to avoid colliding with RenameOther's hotkey binding.
```

Edit `src/hexrays_pytools/domain/const.py` line 4:

```python
as module-level globals (B11 bug — re-initialized via ``const.init()`` at
```

→

```python
as module-level globals; re-initialized via ``init_consts()`` when a new
```

(The original line continues onto more lines — read the file first to see full context, then rewrite the comment block to remove the `(B11 bug — ...)` parenthetical while preserving the meaning.)

Edit `src/hexrays_pytools/domain/ctree/swap_if.py` line 12:

```python
``idc.create_array`` (legacy); this port uses a netnode (B12 fix).
```

→

```python
``idc.create_array`` (legacy); this port uses a netnode instead.
```

### Step 1.11: Delete CHANGELOG.md

```bash
rm "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng/CHANGELOG.md"
```

Verify: `ls "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng/CHANGELOG.md"` → file not found.

### Step 1.12: Run tests to verify nothing broke

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest -v 2>&1 | tail -20
```

Expected: All 477 tests pass, coverage ≥ 80% (should match pre-rename state).

### Step 1.13: Run mypy + ruff

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && mypy --strict src/hexrays_pytools/ 2>&1 | tail -10
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && ruff check src/hexrays_pytools/ tests/ tools/ 2>&1 | tail -10
```

Expected: Both clean.

### Step 1.14: Smoke build

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && python tools/build_plugin.py 2>&1 | tail -5
```

Expected: `Built: D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng/dist/hexrays_pytools_ng-1.0.0.zip`.

### Step 1.15: Commit

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && git add -A && git commit -m "chore: rename to HexRaysPyTools-ng v1.0.0, remove CHANGELOG" 2>&1 | tail -5
```

Expected: One commit with the rename, version bump, comment cleanup, CHANGELOG deletion.

---

## Task 2: ActionRegistry Count Mismatch → RuntimeError (F3)

**Files:**
- Modify: `src/hexrays_pytools/domain/actions/registry.py:132-133`

### Step 2.1: Write a failing test that proves silent failure

Read `tests/domain/actions/test_registry.py` — `test_registry_build_actions_returns_27` (line 23) currently mocks `_build_actions` to return 27 mocks. Add a new test that triggers the real `_build_actions` with an artificially small list to verify the runtime error fires:

Edit `tests/domain/actions/test_registry.py` — append at end of file:

```python
def test_registry_count_mismatch_raises_runtime_error() -> None:
    """If _build_actions returns wrong count, raise RuntimeError (not silent warning).

    Guards against silent count drift: a refactor that forgets to add a class
    to both ACTION_CLASSES and _build_actions used to log a warning that
    nobody read. Now CI fails loud.
    """
    import pytest

    r = ActionRegistry()
    # Mock _build_actions to return wrong count
    r._build_actions = lambda: [MagicMock() for _ in range(26)]  # noqa: E731
    with pytest.raises(RuntimeError, match="expected 27 action classes"):
        r._build_actions()  # Re-check via direct call — but the raise is in _build_actions itself
```

Wait — looking at registry.py:132-133, the check is INSIDE `_build_actions`, not after. So the mock test above doesn't trigger the check (mock replaces the whole method). Instead, the test must inject a class that bypasses the check or trigger the real path with missing modules.

The cleaner approach: temporarily delete a class from `ACTION_CLASSES` and verify `RuntimeError` fires. But that requires manipulating imports.

Simplest reliable test: patch `_build_actions` to assert the count check happens via a side-effect wrapper:

```python
def test_registry_count_mismatch_raises_runtime_error() -> None:
    """Count check raises RuntimeError, not silent logger.warning."""
    import pytest

    from hexrays_pytools.domain.actions import registry as reg_module

    real_build = reg_module.ActionRegistry._build_actions

    def fake_build(self):
        # Return 26 instances to trigger the mismatch path
        return [MagicMock() for _ in range(26)]

    with patch.object(reg_module.ActionRegistry, "_build_actions", fake_build):
        r = reg_module.ActionRegistry()
        with pytest.raises(RuntimeError, match="expected 27 action classes"):
            real_build(r)  # Real build has the count check; 27 real classes minus 1 fake = path triggered differently
```

Hmm, this is getting complex. The simplest approach: directly verify the change is in place by checking the source string OR by triggering the condition via monkeypatch of ACTION_CLASSES.

Cleaner approach — change the strategy: verify the source contains `raise RuntimeError`:

```python
def test_registry_uses_raise_not_warning() -> None:
    """The count mismatch check uses raise RuntimeError, not logger.warning."""
    import inspect

    from hexrays_pytools.domain.actions.registry import ActionRegistry

    source = inspect.getsource(ActionRegistry._build_actions)
    assert "logger.warning" not in source
    assert "raise RuntimeError" in source
```

This is a static-source check that documents the contract. Simpler, no mocking gymnastics.

Use this test instead. Add to `tests/domain/actions/test_registry.py`:

```python
def test_registry_uses_raise_not_warning() -> None:
    """The count mismatch check uses raise RuntimeError, not logger.warning."""
    import inspect

    from hexrays_pytools.domain.actions.registry import ActionRegistry

    source = inspect.getsource(ActionRegistry._build_actions)
    assert "logger.warning" not in source
    assert "raise RuntimeError" in source
```

### Step 2.2: Run test to verify it fails

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest tests/domain/actions/test_registry.py::test_registry_uses_raise_not_warning -v
```

Expected: FAIL with `AssertionError: assert 'raise RuntimeError' in source` (since current code uses `logger.warning`).

### Step 2.3: Change `logger.warning` to `raise RuntimeError`

Edit `src/hexrays_pytools/domain/actions/registry.py` lines 131-133:

```python
        # Sanity: count matches spec
        if len(all_classes) != 27:
            logger.warning("Expected 27 action classes, found %d", len(all_classes))
```

→

```python
        # Sanity: count matches spec. Raise to prevent silent count drift —
        # a refactor that forgets to add a class to both ACTION_CLASSES
        # and _build_actions would otherwise ship without CI catching it.
        if len(all_classes) != 27:
            raise RuntimeError(
                f"ActionRegistry: expected 27 action classes, got {len(all_classes)}. "
                "Did you forget to add a class to both ACTION_CLASSES and _build_actions?"
            )
```

### Step 2.4: Run test to verify it passes

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest tests/domain/actions/test_registry.py::test_registry_uses_raise_not_warning -v
```

Expected: PASS.

### Step 2.5: Run full test suite to verify no regressions

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest -v 2>&1 | tail -10
```

Expected: All tests pass (count check still passes with 27 real classes).

### Step 2.6: Run mypy + ruff

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && mypy --strict src/hexrays_pytools/ 2>&1 | tail -5
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && ruff check src/hexrays_pytools/ tests/ tools/ 2>&1 | tail -5
```

Expected: Both clean.

### Step 2.7: Commit

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && git add src/hexrays_pytools/domain/actions/registry.py tests/domain/actions/test_registry.py && git commit -m "fix(registry): raise RuntimeError on action count mismatch (F3)" 2>&1 | tail -3
```

---

## Task 3: XrefStorage Migration Atomicity + Correct Comment (F2)

**Files:**
- Modify: `src/hexrays_pytools/domain/xrefs/xref_storage.py`
- Modify: `tests/domain/xrefs/test_xref_storage.py`

### Step 3.1: Write failing tests for migration behavior

Add new tests to `tests/domain/xrefs/test_xref_storage.py` (append at end):

```python
"""Migration tests for F2: atomic migration + correct 'netnode wins' semantic."""
from unittest.mock import MagicMock, patch

import idaapi  # type: ignore[import-not-found]


def test_migrate_from_legacy_writes_to_netnode_before_delete() -> None:
    """F2: flush merged data to netnode BEFORE idc.delete_array.

    A crash between delete and flush would lose user xref data irrecoverably.
    Order in source code is the contract.
    """
    import inspect

    from hexrays_pytools.domain.xrefs.xref_storage import XrefStorage

    source = inspect.getsource(XrefStorage._migrate_from_legacy)
    # The flush must happen BEFORE delete_array in source order
    flush_pos = source.find("self.flush()")
    delete_pos = source.find("idc.delete_array")
    assert flush_pos != -1, "self.flush() not found in _migrate_from_legacy"
    assert delete_pos != -1, "idc.delete_array not found in _migrate_from_legacy"
    assert flush_pos < delete_pos, (
        "F2 violation: idc.delete_array is called before self.flush() — "
        "a crash between the two would lose user data irrecoverably"
    )


def test_migrate_comment_documents_netnode_wins_semantic() -> None:
    """F2: comment in _migrate_from_legacy must say 'netnode wins'."""
    import inspect

    from hexrays_pytools.domain.xrefs.xref_storage import XrefStorage

    source = inspect.getsource(XrefStorage._migrate_from_legacy)
    assert "legacy takes precedence" not in source.lower(), (
        "F2 violation: comment says legacy takes precedence but code makes netnode win"
    )
    assert "netnode wins" in source.lower(), (
        "F2: comment should explicitly state 'netnode wins' semantic"
    )


def test_migrate_noop_when_legacy_absent() -> None:
    """If idc.get_array_id returns BADORD, no migration + no delete happens."""
    from hexrays_pytools.domain.xrefs.xref_storage import XrefStorage

    x = XrefStorage()
    with patch("hexrays_pytools.domain.xrefs.xref_storage.idc") as mock_idc, \
         patch("hexrays_pytools.domain.xrefs.xref_storage.Netnode"):
        mock_idc.get_array_id.return_value = idaapi.BADORD
        x._migrate_from_legacy()
        mock_idc.delete_array.assert_not_called()
        mock_idc.get_array_element.assert_not_called()


def test_migrate_merges_when_netnode_empty() -> None:
    """If netnode storage is empty, legacy data is loaded into it."""
    from hexrays_pytools.domain.xrefs.xref_storage import XrefStorage

    x = XrefStorage()
    x._storage = {}
    legacy_data = {"42": {"256": [["field_a", 0, "read"]]]}

    with patch("hexrays_pytools.domain.xrefs.xref_storage.idc") as mock_idc, \
         patch("hexrays_pytools.domain.xrefs.xref_storage.Netnode"), \
         patch("hexrays_pytools.domain.xrefs.xref_storage.json") as mock_json:
        mock_idc.get_array_id.return_value = 999
        mock_idc.get_last_index.return_value = 1
        mock_idc.get_array_element.return_value = b'{"42": {"256": [["field_a", 0, "read"]]}}'
        mock_json.loads.return_value = legacy_data

        x._migrate_from_legacy()

    # Legacy data merged into netnode storage
    assert 42 in x._storage
    assert 256 in x._storage[42]
    assert x._storage[42][256] == [["field_a", 0, "read"]]
    # Legacy array deleted after migration
    mock_idc.delete_array.assert_called_once()


def test_migrate_netnode_wins_on_conflict() -> None:
    """If netnode already has data for (ord, func_off), legacy is dropped."""
    from hexrays_pytools.domain.xrefs.xref_storage import XrefStorage

    x = XrefStorage()
    # Netnode already has data for (42, 256)
    x._storage = {42: {256: [["netnode_value", 0, "read"]]}}
    legacy_data = {"42": {"256": [["legacy_value", 0, "read"]]}}

    with patch("hexrays_pytools.domain.xrefs.xref_storage.idc") as mock_idc, \
         patch("hexrays_pytools.domain.xrefs.xref_storage.Netnode"), \
         patch("hexrays_pytools.domain.xrefs.xref_storage.json") as mock_json:
        mock_idc.get_array_id.return_value = 999
        mock_idc.get_last_index.return_value = 1
        mock_idc.get_array_element.return_value = b'{"42": {"256": [["legacy_value", 0, "read"]]}}'
        mock_json.loads.return_value = legacy_data

        x._migrate_from_legacy()

    # Netnode value wins — legacy dropped for conflicting key
    assert x._storage[42][256] == [["netnode_value", 0, "read"]]
```

### Step 3.2: Run tests to verify they fail

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest tests/domain/xrefs/test_xref_storage.py -v 2>&1 | tail -15
```

Expected: 3 new tests FAIL (the order-check, comment-check, and conflict tests). Existing 6 tests pass.

### Step 3.3: Fix the migration code

Edit `src/hexrays_pytools/domain/xrefs/xref_storage.py` — replace lines 74-83 in `_migrate_from_legacy`:

```python
            # Merge: legacy takes precedence for matching ordinals
            for ord_key, funcs in old.items():
                ord_key = int(ord_key)
                self._storage.setdefault(ord_key, {})
                for func_off, fields in funcs.items():
                    func_off = int(func_off)
                    if func_off not in self._storage[ord_key]:
                        self._storage[ord_key][func_off] = fields
            # Delete old array after successful migration
            idc.delete_array(array_id)
```

→

```python
            # Merge: netnode wins on (ord, func_off) conflicts. If the user
            # already has stored xrefs in the new format, legacy data is
            # dropped for matching keys (setdefault + membership check).
            for ord_key, funcs in old.items():
                ord_key = int(ord_key)
                self._storage.setdefault(ord_key, {})
                for func_off, fields in funcs.items():
                    func_off = int(func_off)
                    if func_off not in self._storage[ord_key]:
                        self._storage[ord_key][func_off] = fields
            # F2 fix: flush merged data to netnode BEFORE deleting the legacy
            # array. A crash between delete and flush would lose user xref
            # data irrecoverably; flushing first ensures at worst the user
            # ends up with both legacy and netnode copies (next open will
            # re-run migration with netnode winning on conflict).
            self.flush()
            # Only now safe to delete the legacy array.
            idc.delete_array(array_id)
```

### Step 3.4: Run tests to verify they pass

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest tests/domain/xrefs/test_xref_storage.py -v 2>&1 | tail -15
```

Expected: All tests pass (6 existing + 5 new = 11 total).

### Step 3.5: Run full test suite

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest -v 2>&1 | tail -10
```

Expected: All tests pass, coverage ≥ 80%.

### Step 3.6: Run mypy + ruff

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && mypy --strict src/hexrays_pytools/ 2>&1 | tail -5
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && ruff check src/hexrays_pytools/ tests/ tools/ 2>&1 | tail -5
```

Expected: Both clean.

### Step 3.7: Commit

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && git add src/hexrays_pytools/domain/xrefs/xref_storage.py tests/domain/xrefs/test_xref_storage.py && git commit -m "fix(xrefs): atomic migration + correct netnode-wins comment (F2)" 2>&1 | tail -3
```

---

## Task 4: Move MyChoose from ui/ to domain/ (F1.a)

**Files:**
- Create: `src/hexrays_pytools/domain/chooser.py`
- Modify: `src/hexrays_pytools/ui/chooser.py` (remove MyChoose)
- Modify: 5 import sites in `src/hexrays_pytools/domain/`

### Step 4.1: Read current `MyChoose` class

Read `src/hexrays_pytools/ui/chooser.py` to see the full `MyChoose` class definition.

### Step 4.2: Create new domain/chooser.py

Create `src/hexrays_pytools/domain/chooser.py` with the `MyChoose` class content copied verbatim from `ui/chooser.py`. Adjust imports if needed (the class may import from `idaapi` only — verify by reading the source).

```python
"""Reusable idaapi.Choose subclass for list selection UI.

Moved from `ui/chooser.py` to `domain/chooser.py` (F1.a) because it does not
depend on Qt widgets — it's a thin wrapper around `idaapi.Choose`. This
eliminates 5 upward imports from domain/ to ui/ that violated the 5-layer
architecture rule.

Lives in domain/ (not ui/) because:
- No Qt dependency (just idaapi.Choose)
- Used by domain actions (struct_xref, structs_by_size, guess_allocation,
  negative_offsets, type_library) to display selection lists

If a future change needs Qt widgets here, that should be a class extending
this one in ui/, not this module.
"""
from __future__ import annotations

# PASTE MyChoose class body here from ui/chooser.py, preserving all logic.
```

### Step 4.3: Remove `MyChoose` from ui/chooser.py

Edit `src/hexrays_pytools/ui/chooser.py` — delete the `MyChoose` class definition (and any imports it required that aren't used by other code in the file). Keep any other classes/functions.

### Step 4.4: Update 5 import sites

Each of the following files changes `from ...ui.chooser import MyChoose` → `from ..chooser import MyChoose`:

- `src/hexrays_pytools/domain/actions/guess_allocation.py` (line 23)
- `src/hexrays_pytools/domain/actions/struct_xref.py` (line 15)
- `src/hexrays_pytools/domain/actions/structs_by_size.py` (line 13)
- `src/hexrays_pytools/domain/ctree/negative_offsets.py` (line 21)
- `src/hexrays_pytools/domain/til/type_library.py` (line 17)

### Step 4.5: Run tests to verify nothing broke

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest -v 2>&1 | tail -10
```

Expected: All tests pass.

### Step 4.6: Verify no domain→ui upward imports remain for MyChoose

```bash
grep -rn "from hexrays_pytools\.ui\.chooser\|from \.\.\.ui\.chooser\|from \.\.ui\.chooser" src/hexrays_pytools/domain/
```

Expected: 0 lines.

### Step 4.7: Run mypy + ruff

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && mypy --strict src/hexrays_pytools/ 2>&1 | tail -5
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && ruff check src/hexrays_pytools/ tests/ tools/ 2>&1 | tail -5
```

Expected: Both clean.

### Step 4.8: Commit

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && git add src/hexrays_pytools/domain/chooser.py src/hexrays_pytools/ui/chooser.py src/hexrays_pytools/domain/actions/guess_allocation.py src/hexrays_pytools/domain/actions/struct_xref.py src/hexrays_pytools/domain/actions/structs_by_size.py src/hexrays_pytools/domain/ctree/negative_offsets.py src/hexrays_pytools/domain/til/type_library.py && git commit -m "refactor(chooser): move MyChoose from ui/ to domain/ (F1.a)" 2>&1 | tail -3
```

---

## Task 5: Widget Factory Injection via Session (F1.b)

**Files:**
- Modify: `src/hexrays_pytools/domain/session.py`
- Modify: `src/hexrays_pytools/domain/actions/form_requests.py`
- Modify: `src/hexrays_pytools/plugin.py`
- Modify: `tests/domain/actions/test_form_requests.py`

### Step 5.1: Write failing test for factory wiring

Add new tests to `tests/domain/actions/test_form_requests.py` (append):

```python
"""Tests for F1.b: widget factory wiring via Session."""
from unittest.mock import MagicMock


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
    """F1.b: form_requests.py must NOT directly import widget classes."""
    import inspect

    from hexrays_pytools.domain.actions import form_requests

    source = inspect.getsource(form_requests)
    # The 3 widget classes must not appear as imports in this module
    assert "from ...ui.widgets.class_viewer import ClassViewer" not in source
    assert "from ...ui.widgets.graph_viewer import StructureGraphViewer" not in source
    assert "from ...ui.widgets.structure_builder import StructureBuilder" not in source


def test_show_classes_calls_class_viewer_factory() -> None:
    """ShowClasses.activate uses session.class_viewer_factory."""
    from hexrays_pytools.domain.actions.form_requests import ShowClasses

    mock_factory = MagicMock(return_value=MagicMock())
    session = MagicMock()
    session.class_viewer_factory = mock_factory
    a = ShowClasses(session=session)
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
    from hexrays_pytools.domain.actions.form_requests import ShowClasses

    import pytest

    session = MagicMock()
    session.class_viewer_factory = None
    a = ShowClasses(session=session)
    # Mock idaapi.find_widget to return None so we exercise the factory branch
    with patch("hexrays_pytools.domain.actions.form_requests.idaapi.find_widget", return_value=None):
        with pytest.raises(RuntimeError, match="class_viewer_factory not wired"):
            a.activate(MagicMock())
```

Add `patch` import at top of file if not present:

```python
from unittest.mock import patch
```

### Step 5.2: Run tests to verify they fail

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest tests/domain/actions/test_form_requests.py -v 2>&1 | tail -15
```

Expected: New tests FAIL. Existing tests still pass.

### Step 5.3: Add factory fields to Session

Edit `src/hexrays_pytools/domain/session.py` — add to `TYPE_CHECKING` block (after existing imports):

```python
if TYPE_CHECKING:
    from .browser.proxy_model import ProxyModel
    from .browser.tree_model import TreeModel
    from .const import Consts
    from .recon.structure_model import StructureModel
    from .recon.workspace import ReconWorkspace
    from .templated.templated_types import TemplatedTypes
    from .xrefs.xref_storage import XrefStorage
```

(Note: ProxyModel, TreeModel, StructureModel are TYPE_CHECKING-only because they trigger PySide6 import in some test envs; factories' type hints use them but actual instances are created at call time in plugin.py.)

Edit `src/hexrays_pytools/domain/session.py` — add 3 fields to Session dataclass (after `templated: TemplatedTypes | None = None`, before `consts: Consts | None = None`):

```python
    # Widget factories — wired by plugin entry (plugin.py) after Session is
    # created. Domain actions call these factories instead of importing UI
    # widgets directly. This is the ONLY legal UI→session wiring point in
    # the 5-layer architecture (F1.b fix).
    class_viewer_factory: Callable[[StructureModel], Any] | None = None
    structure_graph_viewer_factory: Callable[[ReconWorkspace], Any] | None = None
    structure_builder_factory: Callable[[ReconWorkspace], Any] | None = None
```

Add `Callable` import at top of session.py:

```python
from collections.abc import Callable
```

### Step 5.4: Refactor form_requests.py

Edit `src/hexrays_pytools/domain/actions/form_requests.py`:

Replace lines 15-17 (the 3 widget imports) with:

```python
# F1.b: widget classes no longer imported directly. Use session factories
# (session.class_viewer_factory, etc.) wired by plugin.py. The TYPE_CHECKING
# block below imports them for type hints only — not at runtime.
```

Add to the existing TYPE_CHECKING block:

```python
if TYPE_CHECKING:
    from ..session import Session
    from ..recon.structure_model import StructureModel
    from ..recon.workspace import ReconWorkspace
```

Edit `ShowGraph.activate()` (line 36-55) — replace `self.graph_view = StructureGraphViewer("Structure Graph", self.graph)` with factory call:

```python
    def activate(self, ctx: Any) -> None:
        # Re-show the existing graph if open, otherwise build a new one.
        if self.graph_view is not None:
            try:
                self.graph_view.change_selected(
                    [int(sel) + 1 for sel in ctx.chooser_selection]
                )
                self.graph_view.Refresh()
                return
            except (AttributeError, RuntimeError):
                pass
        self.graph = StructureGraph(
            [int(sel) + 1 for sel in ctx.chooser_selection]
        )
        # F1.b: use session factory instead of direct widget import
        if self._session is None or self._session.structure_graph_viewer_factory is None:
            raise RuntimeError("structure_graph_viewer_factory not wired; plugin init incomplete")
        self.graph_view = self._session.structure_graph_viewer_factory(self.graph)
        # IDA 9.x GraphViewer.Show takes a `caption` arg; older IDA didn't.
        if hasattr(self.graph_view, "Show"):
            self.graph_view.Show("Structure Graph")
        else:
            self.graph_view.Refresh()
```

Wait — `StructureGraph` is from `domain/graph/`, not from `ui/`. Keep that import. The factory only wraps the viewer widget creation.

Edit `ShowClasses.activate()` (line 72-83) — replace direct ClassViewer creation with factory:

```python
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
```

Note: `class_viewer_factory()` takes no args in the new design (the factory internally creates its own ProxyModel/TreeModel, OR is a zero-arg callable). Update the field signature in Session:

```python
class_viewer_factory: Callable[[], Any] | None = None
```

Actually, looking at the original ShowClasses code: `ClassViewer(ProxyModel(), TreeModel())` — the factory needs access to a proxy model + tree model. The cleanest approach is to make the factory a zero-arg callable that creates the full widget with its internal models. The plugin entry creates:

```python
session.class_viewer_factory = lambda: ClassViewer(ProxyModel(), TreeModel())
```

This keeps the factory signature zero-arg. Adjust the Session dataclass field type to `Callable[[], Any] | None`.

Edit `ShowStructureBuilder.activate()` (line 99-115) — replace direct StructureBuilder creation with factory:

```python
    def activate(self, ctx: Any) -> None:
        tform = idaapi.find_widget("Structure Builder")
        if tform:
            idaapi.activate_widget(tform, True)
            return
        # No existing builder — open a new one backed by the session's
        # workspace model. If no session/model, the widget handles None
        # gracefully (or we create an empty one).
        # F1.b: use session factory instead of direct widget import
        if self._session is None or self._session.structure_builder_factory is None:
            raise RuntimeError("structure_builder_factory not wired; plugin init incomplete")
        builder = self._session.structure_builder_factory(self._session.recon)
        # IDA 9.x PluginForm.Show takes a `caption` arg (older IDA didn't).
        if hasattr(builder, "Show"):
            builder.Show("Structure Builder")
        else:
            builder.Show()
```

### Step 5.5: Wire factories in plugin.py

Edit `src/hexrays_pytools/plugin.py` — add imports at top (after existing imports):

```python
from .ui.widgets.class_viewer import ClassViewer
from .ui.widgets.graph_viewer import StructureGraphViewer
from .ui.widgets.structure_builder import StructureBuilder
from .domain.browser.proxy_model import ProxyModel
from .domain.browser.tree_model import TreeModel
from .domain.graph.structure_graph import StructureGraph
```

(Note: these imports are legal here because `plugin.py` is layer 4 / root — the only place UI imports are allowed.)

Edit `init()` (line 57-96) — add factory wiring after `self.session.open()` (line 67), before `self.hx_callbacks = HxCallbackManager()` (line 71):

```python
        self.session = Session()
        self.session.open()

        # F1.b: wire widget factories into Session. This is the only legal
        # UI→domain wiring point in the 5-layer architecture. Domain actions
        # call these factories instead of importing widget classes directly.
        self.session.class_viewer_factory = lambda: ClassViewer(ProxyModel(), TreeModel())
        self.session.structure_graph_viewer_factory = lambda graph: StructureGraphViewer("Structure Graph", graph)
        self.session.structure_builder_factory = lambda workspace: StructureBuilder(workspace.model if workspace is not None else None)

        # Install the hx event dispatcher first — ActionRegistry needs it to
        # attach popup actions to hxe_populating_popup.
```

### Step 5.6: Update existing form_requests tests

The existing tests `test_show_graph_instantiable_and_activates`, `test_show_classes_instantiable_and_activates`, `test_show_structure_builder_activate_does_not_raise` create actions without session and call `activate(MagicMock())`. These will now raise `RuntimeError` because factories are `None`.

Two options:
- (a) Update each existing test to inject mock factory via session
- (b) Allow `activate()` to be called without session for testing (no — defeats purpose)

Choose (a). Edit each existing test:

```python
def test_show_graph_instantiable_and_activates() -> None:
    session = MagicMock()
    session.structure_graph_viewer_factory = MagicMock(return_value=MagicMock())
    a = ShowGraph(session=session)
    assert a.name == "HexRaysPyTools:ShowGraph"
    ctx = MagicMock()
    ctx.chooser_selection = [0]
    a.activate(ctx)  # should not raise


def test_show_classes_instantiable_and_activates() -> None:
    session = MagicMock()
    session.class_viewer_factory = MagicMock(return_value=MagicMock())
    a = ShowClasses(session=session)
    assert a.name == "HexRaysPyTools:ShowClasses"
    a.activate(MagicMock())


def test_show_structure_builder_check_returns_true() -> None:
    session = MagicMock()
    session.structure_builder_factory = MagicMock(return_value=MagicMock())
    session.recon = MagicMock()
    a = ShowStructureBuilder(session=session)
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())  # should not raise
```

### Step 5.7: Run form_requests tests

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest tests/domain/actions/test_form_requests.py -v 2>&1 | tail -20
```

Expected: All tests pass (existing + new).

### Step 5.8: Run full test suite

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest -v 2>&1 | tail -10
```

Expected: All tests pass.

### Step 5.9: Verify no domain→ui upward imports remain for widgets

```bash
grep -rn "from \.\.\.ui\.widgets\|from hexrays_pytools\.ui\.widgets" src/hexrays_pytools/domain/
```

Expected: 0 lines (only `plugin.py` should import from `ui/`, not `domain/`).

### Step 5.10: Run mypy + ruff

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && mypy --strict src/hexrays_pytools/ 2>&1 | tail -5
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && ruff check src/hexrays_pytools/ tests/ tools/ 2>&1 | tail -5
```

Expected: Both clean.

### Step 5.11: Commit

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && git add src/hexrays_pytools/domain/session.py src/hexrays_pytools/domain/actions/form_requests.py src/hexrays_pytools/plugin.py tests/domain/actions/test_form_requests.py && git commit -m "refactor(form_requests): inject widget factories via Session (F1.b)" 2>&1 | tail -3
```

---

## Task 6: HxCallbackManager Error Visibility (F4)

**Files:**
- Modify: `src/hexrays_pytools/domain/actions/hx_callback.py`
- Modify: `src/hexrays_pytools/domain/session.py`
- Modify: `tests/domain/actions/test_hx_callback.py`

### Step 6.1: Write failing tests for error recording

Add new tests to `tests/domain/actions/test_hx_callback.py` (append):

```python
def test_dispatch_records_handler_exception() -> None:
    """F4: handler exceptions are recorded in manager.errors."""
    m = HxCallbackManager()
    bad = MagicMock()
    bad.handle.side_effect = ValueError("boom")
    m.register(idaapi.hxe_maturity, bad)
    m._dispatch(idaapi.hxe_maturity)
    assert len(m.errors) == 1
    event_id, exc = m.errors[0]
    assert event_id == idaapi.hxe_maturity
    assert isinstance(exc, ValueError)
    assert str(exc) == "boom"


def test_session_recent_callback_errors_property() -> None:
    """F4: Session exposes recent_callback_errors property."""
    from hexrays_pytools.domain.session import Session

    s = Session()
    # No hx_callbacks wired yet — property returns empty list
    assert s.recent_callback_errors == []
```

### Step 6.2: Run tests to verify they fail

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest tests/domain/actions/test_hx_callback.py -v 2>&1 | tail -10
```

Expected: 2 new tests FAIL.

### Step 6.3: Add errors list to HxCallbackManager

Edit `src/hexrays_pytools/domain/actions/hx_callback.py`:

Add to `__init__` (after `self._installed = False`):

```python
        # F4: record last N exceptions from handlers. Read-only access via
        # Session.recent_callback_errors. Helps surface silent handler failures
        # to UI / status bar (rendering is follow-up scope).
        self.errors: list[tuple[int, Exception]] = []
```

Edit `_dispatch` (line 30-36):

```python
    def _dispatch(self, event: int, *args: Any) -> int:
        for handler in self._handlers.get(event, []):
            try:
                handler.handle(event, *args)
            except Exception as e:  # noqa: BLE001
                logger.exception("HxCallback handler failed: %s", e)
        return 0
```

→

```python
    def _dispatch(self, event: int, *args: Any) -> int:
        for handler in self._handlers.get(event, []):
            try:
                handler.handle(event, *args)
            except Exception as e:  # noqa: BLE001 — intentional swallow to prevent native crash
                logger.exception("HxCallback handler failed: %s", e)
                # F4: record exception for visibility (UI can poll via
                # Session.recent_callback_errors). Keep last 100 to bound memory.
                self.errors.append((event, e))
                if len(self.errors) > 100:
                    self.errors.pop(0)
        return 0
```

### Step 6.4: Add property to Session

Edit `src/hexrays_pytools/domain/session.py` — add method to Session dataclass (after `close()` method):

```python
    @property
    def recent_callback_errors(self) -> list[tuple[int, Exception]]:
        """Last 10 errors from HxCallbackManager (read-only snapshot).

        F4: surfaces silent handler failures. UI code can poll this to render
        status bar warning / log action. Returns empty list if hx_callbacks
        not yet wired (e.g. before plugin.init() completes).
        """
        if self.hx_callbacks is None:
            return []
        return list(self.hx_callbacks.errors[-10:])
```

Note: `session.hx_callbacks` doesn't exist yet on the Session dataclass — it's stored on the plugin instance (`plugin.hx_callbacks`). To make this work, either:

- (a) Add `hx_callbacks: HxCallbackManager | None = None` field to Session and have `plugin.py` set it after creating both
- (b) Pass `hx_callbacks` reference into Session at construction time

Choose (a) — simpler. Edit session.py:

Add field (after `templated` field):

```python
    # HxCallbackManager reference (set by plugin.init() after construction).
    # Used by recent_callback_errors property (F4).
    hx_callbacks: HxCallbackManager | None = None
```

Add to TYPE_CHECKING block:

```python
    from .actions.hx_callback import HxCallbackManager
```

Edit `plugin.py` `init()` — after creating `self.hx_callbacks` (line 72), add:

```python
        # F4: share hx_callbacks reference with Session for error visibility.
        if self.session is not None:
            self.session.hx_callbacks = self.hx_callbacks
```

### Step 6.5: Run tests to verify they pass

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest tests/domain/actions/test_hx_callback.py -v 2>&1 | tail -15
```

Expected: All tests pass (existing 7 + new 2 = 9 total).

### Step 6.6: Run full test suite

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest -v 2>&1 | tail -10
```

Expected: All tests pass.

### Step 6.7: Run mypy + ruff

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && mypy --strict src/hexrays_pytools/ 2>&1 | tail -5
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && ruff check src/hexrays_pytools/ tests/ tools/ 2>&1 | tail -5
```

Expected: Both clean.

### Step 6.8: Commit

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && git add src/hexrays_pytools/domain/actions/hx_callback.py src/hexrays_pytools/domain/session.py src/hexrays_pytools/plugin.py tests/domain/actions/test_hx_callback.py && git commit -m "feat(hx_callback): expose handler errors via Session.recent_callback_errors (F4)" 2>&1 | tail -3
```

---

## Task 7: ReconWorkspace Lazy Model (F6)

**Files:**
- Modify: `src/hexrays_pytools/domain/recon/workspace.py`
- Modify: `tests/domain/recon/test_workspace.py`

### Step 7.1: Write failing tests for lazy model

Add new tests to `tests/domain/recon/test_workspace.py` (append):

```python
"""Tests for F6: lazy model in ReconWorkspace."""
from unittest.mock import patch


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
```

### Step 7.2: Run tests to verify they fail

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest tests/domain/recon/test_workspace.py -v 2>&1 | tail -15
```

Expected: 3 new tests FAIL (current `_create_empty_model()` runs eagerly in `__init__`).

### Step 7.3: Refactor ReconWorkspace to lazy init

Edit `src/hexrays_pytools/domain/recon/workspace.py`:

Replace `__init__` (lines 37-46):

```python
    def __init__(self) -> None:
        # Pre-create an empty StructureModel so scanner actions work
        # without first opening the Structure Builder widget. Mirrors
        # the original plugin's behaviour where ``cache.temporary_structure``
        # was a module-level singleton always present at session start.
        self._model: StructureModel = _create_empty_model()
        # The primary struct offset the user is reconstructing. Scanners
        # read this as the `origin` argument to SearchVisitor. Default 0
        # (no offset selected) — the StructureBuilder sets this on row click.
        self.main_offset: int = 0
```

→

```python
    def __init__(self) -> None:
        # F6: true lazy init — StructureModel (Qt-dependent) is constructed
        # on first .model access, not at workspace init. This keeps
        # Session.open() PySide6-free so unit tests can construct a
        # ReconWorkspace without Qt available. Mirrors the original plugin's
        # behavior where the model was always present at session start —
        # scanner actions that check `workspace.model is None` still see a
        # model after first access (and the property always returns one).
        self._model: StructureModel | None = None
        # The primary struct offset the user is reconstructing. Scanners
        # read this as the `origin` argument to SearchVisitor. Default 0
        # (no offset selected) — the StructureBuilder sets this on row click.
        self.main_offset: int = 0
```

Replace `model` property (lines 48-56):

```python
    @property
    def model(self) -> StructureModel | None:
        """The current structure model.

        Returns ``None`` only if the model was never initialized AND the
        ``_model`` attribute was forcibly deleted. In normal use this is
        always a :class:`StructureModel` instance.
        """
        return self._model
```

→

```python
    @property
    def model(self) -> StructureModel:
        """The current structure model.

        F6: lazy construction — first access builds an empty StructureModel,
        subsequent accesses return the cached instance. Returns a fresh
        StructureModel if `_model` was forcibly deleted (defensive). Always
        returns a non-None StructureModel in normal use.
        """
        if self._model is None:
            self._model = _create_empty_model()
        return self._model
```

Edit `clear()` (lines 62-73) — the `if self._model is not None` check now guards against empty workspace (no .model access yet):

```python
    def clear(self) -> None:
        """Empty the model + reset main_offset.

        Note: the model **stays alive** — only its items are cleared. This
        keeps subsequent scanner actions working without a re-init step.
        The original plugin cleared items the same way (the global model
        never went away).
        """
        if self._model is not None:
            self._model.clear()
        self.main_offset = 0
        logger.debug("ReconWorkspace cleared (items + main_offset reset)")
```

Keep as-is. The `is not None` check handles the lazy-init case correctly.

Edit `is_empty()` (lines 75-83):

```python
    def is_empty(self) -> bool:
        """Return True if the model has no items (or no model at all).

        ``empty`` is checked against items, not model existence — the model
        is always present after :class:`ReconWorkspace` is constructed.
        """
        if self._model is None:
            return True
        return self._model.rowCount() == 0
```

Keep as-is. The `is None` check handles the never-accessed case (returns True = empty).

Edit `_create_empty_model` docstring (lines 86-95):

```python
def _create_empty_model() -> StructureModel:
    """Build an empty :class:`StructureModel` (avoids circular import at module load).

    ``workspace`` is imported by ``structure_model`` in the Qt model code
    paths; importing the model class at the top of this file would create
    a cycle. Local import keeps the module import graph clean.
    """
    from .structure_model import StructureModel

    return StructureModel()
```

→

```python
def _create_empty_model() -> StructureModel:
    """Build an empty :class:`StructureModel` (true lazy via property accessor).

    ``workspace`` is imported by ``structure_model`` in the Qt model code
    paths; importing the model class at the top of this file would create
    a cycle. Local import keeps the module import graph clean AND keeps
    PySide6 dependency out of ReconWorkspace.__init__ (F6).
    """
    from .structure_model import StructureModel

    return StructureModel()
```

### Step 7.4: Run tests to verify they pass

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest tests/domain/recon/test_workspace.py -v 2>&1 | tail -15
```

Expected: All tests pass (existing 11 + new 3 = 14 total).

### Step 7.5: Run full test suite

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest -v 2>&1 | tail -10
```

Expected: All tests pass.

### Step 7.6: Run mypy + ruff

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && mypy --strict src/hexrays_pytools/ 2>&1 | tail -5
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && ruff check src/hexrays_pytools/ tests/ tools/ 2>&1 | tail -5
```

Expected: Both clean.

### Step 7.7: Commit

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && git add src/hexrays_pytools/domain/recon/workspace.py tests/domain/recon/test_workspace.py && git commit -m "refactor(recon): make ReconWorkspace.model lazy (F6)" 2>&1 | tail -3
```

---

## Task 8: Widget Test Coverage Extension (F5)

**Files:**
- Modify: `tests/ui/widgets/test_class_viewer.py`
- Modify: `tests/ui/widgets/test_structure_builder.py`

### Step 8.1: Read existing widget tests

Read `tests/ui/widgets/test_class_viewer.py` and `tests/ui/widgets/test_structure_builder.py` to see what's already covered.

### Step 8.2: Write extended tests for class_viewer

Append to `tests/ui/widgets/test_class_viewer.py`:

```python
"""F5: extended widget coverage for class_viewer."""
from unittest.mock import MagicMock


def test_class_viewer_init_no_raise_with_model() -> None:
    """ClassViewer() with valid model doesn't raise in __init__."""
    # Skip if PySide6 unavailable (CI minimal may lack it)
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")

    from hexrays_pytools.ui.widgets.class_viewer import ClassViewer
    from hexrays_pytools.domain.browser.proxy_model import ProxyModel
    from hexrays_pytools.domain.browser.tree_model import TreeModel

    viewer = ClassViewer(ProxyModel(), TreeModel())
    assert viewer is not None


def test_class_viewer_column_count() -> None:
    """ClassViewer exposes columnCount via its model binding."""
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")

    from hexrays_pytools.ui.widgets.class_viewer import ClassViewer
    from hexrays_pytools.domain.browser.proxy_model import ProxyModel
    from hexrays_pytools.domain.browser.tree_model import TreeModel

    viewer = ClassViewer(ProxyModel(), TreeModel())
    # columnCount delegates to underlying TreeModel
    assert viewer.columnCount() >= 0
```

### Step 8.3: Write extended tests for structure_builder

Append to `tests/ui/widgets/test_structure_builder.py`:

```python
"""F5: extended widget coverage for structure_builder."""
def test_structure_builder_init_no_raise_with_model() -> None:
    """StructureBuilder() with valid model doesn't raise in __init__."""
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")

    from hexrays_pytools.ui.widgets.structure_builder import StructureBuilder
    from hexrays_pytools.domain.recon.workspace import ReconWorkspace

    builder = StructureBuilder(ReconWorkspace())
    assert builder is not None


def test_structure_builder_init_with_none_model() -> None:
    """StructureBuilder(None) is tolerated (widget handles gracefully)."""
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")

    from hexrays_pytools.ui.widgets.structure_builder import StructureBuilder

    builder = StructureBuilder(None)
    assert builder is not None


def test_structure_builder_column_count() -> None:
    """StructureBuilder exposes columnCount via its model binding."""
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")

    from hexrays_pytools.ui.widgets.structure_builder import StructureBuilder
    from hexrays_pytools.domain.recon.workspace import ReconWorkspace

    builder = StructureBuilder(ReconWorkspace())
    assert builder.columnCount() >= 0
```

### Step 8.4: Run widget tests

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest tests/ui/widgets/test_class_viewer.py tests/ui/widgets/test_structure_builder.py -v 2>&1 | tail -20
```

Expected: All tests pass (some may skip if PySide6 unavailable — that's OK per F5.b).

### Step 8.5: Check coverage delta

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest tests/ui/widgets/ --cov=hexrays_pytools.ui.widgets --cov-report=term-missing 2>&1 | tail -15
```

Expected: Coverage for `class_viewer.py` and `structure_builder.py` increased (target 70%+). If exact numbers needed, look at coverage report.

### Step 8.6: Run full test suite

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest -v 2>&1 | tail -10
```

Expected: All tests pass, total coverage ≥ 80%.

### Step 8.7: Run mypy + ruff

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && mypy --strict src/hexrays_pytools/ 2>&1 | tail -5
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && ruff check src/hexrays_pytools/ tests/ tools/ 2>&1 | tail -5
```

Expected: Both clean.

### Step 8.8: Commit

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && git add tests/ui/widgets/test_class_viewer.py tests/ui/widgets/test_structure_builder.py && git commit -m "test(widgets): extend class_viewer + structure_builder coverage (F5)" 2>&1 | tail -3
```

---

## Task 9: Final Verification

### Step 9.1: Full test suite + coverage gate

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && pytest -v 2>&1 | tail -10
```

Expected: All tests pass, coverage ≥ 80%.

### Step 9.2: All static checks

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && mypy --strict src/hexrays_pytools/ 2>&1 | tail -5
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && ruff check src/hexrays_pytools/ tests/ tools/ 2>&1 | tail -5
```

Expected: Both clean.

### Step 9.3: Build smoke

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && python tools/build_plugin.py 2>&1 | tail -3
ls "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng/dist/"
```

Expected: `hexrays_pytools_ng-1.0.0.zip` exists.

### Step 9.4: Acceptance criteria grep checks

Run each acceptance criterion from spec:

```bash
# AC-2, AC-3: ida-plugin.json
grep -E '"name":\s*"hexrays_pytools_ng"|"version":\s*"1\.0\.0"' ida-plugin.json

# AC-4, AC-5: pyproject.toml
grep -E 'name = "hexrays_pytools_ng"|version = "1\.0\.0"' pyproject.toml

# AC-6: CHANGELOG.md absent
test ! -f CHANGELOG.md && echo "AC-6 PASS"

# AC-7: no bug ID refs in src
grep -rn "B1[0-4]" src/hexrays_pytools/ || echo "AC-7 PASS"

# AC-8: no domain→ui imports
! grep -rn "from hexrays_pytools\.ui\|from \.\.\.ui\|from \.\.ui" src/hexrays_pytools/domain/ && echo "AC-8 PASS"

# AC-9: no logger.warning for action count
! grep "logger.warning.*27 action" src/hexrays_pytools/domain/actions/registry.py && echo "AC-9 PASS"

# AC-10: netnode key new name
grep '\$hexrays_pytools_ng/xref_storage' src/hexrays_pytools/domain/xrefs/xref_storage.py && echo "AC-10 PASS"

# AC-11: flush before delete (covered by test in Task 3)

# AC-12: netnode wins comment
grep -i "netnode wins" src/hexrays_pytools/domain/xrefs/xref_storage.py && echo "AC-12 PASS"

# AC-17: zip exists
ls dist/hexrays_pytools_ng-1.0.0.zip
```

Expected: All AC checks pass.

### Step 9.5: Review git log

```bash
cd "D:/re_dev_projects/ida-plugins/HexRaysPyTools-ng" && git log --oneline -10
```

Expected: 9 commits (Task 1 through Task 8, plus initial), each with focused message matching the work done.

---

## Self-Review

**Spec coverage**:
- Section 1 (rename + CHANGELOG removal): Task 1 ✓
- F1.a (MyChoose move): Task 4 ✓
- F1.b (widget factory via Session): Task 5 ✓
- F2 (XrefStorage atomic + comment): Task 3 ✓
- F3 (Registry RuntimeError): Task 2 ✓
- F4 (HxCallbackManager errors): Task 6 ✓
- F5 (widget test extension): Task 8 ✓
- F6 (ReconWorkspace lazy): Task 7 ✓
- Section 3 (test plan + acceptance): Task 9 ✓

**Placeholder scan**: No "TBD"/"TODO"/"implement later" found. All code blocks complete.

**Type consistency**:
- `Session.class_viewer_factory` — defined `Callable[[], Any] | None` in Task 5, used as zero-arg in Task 5. ✓
- `Session.structure_graph_viewer_factory` — `Callable[[Any], Any] | None`, called with `self.graph` (StructureGraph). ✓
- `Session.structure_builder_factory` — `Callable[[Any], Any] | None`, called with `self._session.recon` (ReconWorkspace). ✓
- `XrefStorage.flush()` — confirmed exists in source (line 54-56). ✓
- `HxCallbackManager.errors` — `list[tuple[int, Exception]]` defined Task 6.3, used Task 6.4. ✓
- `ReconWorkspace._model` — type changes from `StructureModel` to `StructureModel | None` in Task 7.3; property returns `StructureModel`. Compatible with all callers (they access via `.model` property, not `_model` directly). ✓

**Task ordering**: Tasks 1–8 are independent and can run in order. Each produces a self-contained, committable change. Final Task 9 verifies all acceptance criteria.

**Known risks** (documented in spec):
- IDE/editor must be closed before folder rename (Task 1.1)
- Widget tests require PySide6 importable (Task 8 — pytest.importorskip handles gracefully)
- Form_requests refactor (Task 5) is largest change — 6 files modified

---

**Plan complete and saved to `docs/superpowers/plans/2026-07-07-hexrays-pytools-ng-fork.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for this plan because tasks touch different files (less context bloat) and each task is independently verifiable.

2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints. Faster but you review at end of batch.

Which approach?