# Task 3.4 Report: domain/browser/proxy_model.py

- **Status:** DONE_WITH_CONCERNS
- **Commit:** `25cf611c39b72e2fa05a0e9e9258ee2f75361dd3`
  `feat(browser): add ProxyModel (B3 fix: setFilterRegExp → setFilterRegularExpression)`

## Files

| File | Path |
|------|------|
| Impl | `src/hexrays_pytools/domain/browser/proxy_model.py` |
| Test | `tests/domain/browser/test_proxy_model.py` |

## TDD Summary

- **RED:** Test module failed to import (`ModuleNotFoundError: ...proxy_model`) — confirmed before writing impl.
- **GREEN:** All tests pass. 9/9 (brief specified 7; see "Deviations from brief" below).
- **mypy --strict:** clean (0 errors) on `proxy_model.py`.
- **ruff check:** clean on both files.
- **Env:** `QT_QPA_PLATFORM=offscreen`, `PYTHONPATH=src`, Python 3.14.5, PySide6 installed locally.

```
9 passed in 0.10s
```

## Deviations from brief

The brief was implemented verbatim, with three surgical fixes required to satisfy the strict gates. None change the public API or behavior described in the brief.

### 1. Brief test #7 (`test_filter_accepts_row_matches_name`) is broken as written

PySide6's `setSourceModel()` enforces binding-level type checking and rejects `MagicMock`:

```
TypeError: 'PySide6.QtCore.QSortFilterProxyModel.setSourceModel' called with
wrong argument types: ...setSourceModel(MagicMock)
```

The test passed 6/7 in its verbatim form, then hard-failed on the 7th. To make the brief's test actually exercise `filterAcceptsRow` (its stated intent), I replaced `m.setSourceModel(src)` with `patch.object(m, "sourceModel", return_value=src)` so the override receives a mock source model without going through PySide6's type-checked setter. `from unittest.mock import ... patch` was added to imports.

### 2. Added two complementary tests

To compensate for the brief's single match-path test (which left the `filter_by_function` branch and the non-match rejection path uncovered), I added:

- `test_filter_accepts_row_non_match` — verifies a non-matching name returns `False`.
- `test_filter_accepts_row_by_function` — verifies the `'!'` prefix routes through `node.has_function(...)` and returns its result.

Total: brief's 7 (with #7 fixed) + 2 added = **9 tests, 9 passed**.

### 3. mypy/ruff cleanups on the impl (verbatim source)

The brief's `proxy_model.py` verbatim produced 4 mypy errors and 1 ruff error under the project's strict config:

- **Removed** unused `# type: ignore[import-not-found]` on the `from PySide6 import QtCore` import (PySide6 ships type stubs here; mypy flagged it as unused).
- **Added** `# type: ignore[override]` plus an explanatory comment on `filterAcceptsRow`, mirroring the precedent set in `tree_model.py:118` for the same Qt-signature mismatch (PySide6 stubs declare `parent: QModelIndex | QPersistentModelIndex`; the legacy Qt5 override uses a plain `QModelIndex`).
- **Guarded** `node.has_function(...)` with `node is not None` and wrapped its result in `bool(...)` to satisfy `union-attr` and `no-any-return`.
- **Reformatted** the import block (blank line between stdlib and third-party groups) to satisfy ruff `I001`.

The runtime behavior is identical to the brief's verbatim source.

## B3 fix verified

The B3 fix (the reason this task exists) is in place and tested:

- `set_regexp_filter` calls `self.setFilterRegularExpression(QtCore.QRegularExpression(...))` — never the removed `setFilterRegExp`.
- `filterAcceptsRow` reads `self.filterRegularExpression()` — never the removed `self.filterRegExp().indexIn(...)`.
- Invalid patterns fall back to a no-op filter rather than crashing (test: `test_set_regexp_filter_invalid_falls_back_to_noop`).

## Gate verification commands

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=src pytest tests/domain/browser/test_proxy_model.py -v
# -> 9 passed

python -m mypy --strict src/hexrays_pytools/domain/browser/proxy_model.py
# -> Success: no issues found in 1 source file

python -m ruff check src/hexrays_pytools/domain/browser/proxy_model.py tests/domain/browser/test_proxy_model.py
# -> All checks passed!
```
