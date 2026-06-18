# Task 2.10 Report: domain/recon/structure_model.py

## Status: DONE

## Summary

Implemented `StructureModel` (a `PySide6.QtCore.QAbstractTableModel` subclass) for the
Structure Builder widget, plus its test suite. Two deliverables as specified by the brief:

1. `src/hexrays_pytools/domain/recon/structure_model.py`
2. `tests/domain/recon/test_structure_model.py`

## TDD Summary

| Phase   | Result |
|---------|--------|
| RED     | Wrote test file first; ran `pytest` → `ModuleNotFoundError: No module named 'hexrays_pytools.domain.recon.structure_model'` (5 tests failed to collect). Confirmed RED. |
| GREEN   | Implemented `StructureModel`; all 5 tests pass: `test_model_init_empty`, `test_model_header_data`, `test_model_with_items`, `test_model_add_row_inserts_sorted`, `test_model_clear`. |
| REFACTOR | Cleaned imports, fixed ruff/mypy violations (see Deviations). |

Verification (all green):
- `QT_QPA_PLATFORM=offscreen PYTHONPATH=src pytest tests/domain/recon/test_structure_model.py -v` → 5/5 passed.
- `python -m mypy --strict src/hexrays_pytools/domain/recon/structure_model.py` → Success: no issues.
- `python -m ruff check src/hexrays_pytools/domain/recon/structure_model.py tests/domain/recon/test_structure_model.py` → All checks passed.
- Full suite: 120 passed, coverage 82.43% (≥80% gate met).

## Deviations From Verbatim Brief

The brief said files should be "verbatim" but also required "mypy/ruff clean". The
verbatim content as written fails the project's strict `ruff` (N802, B008, F401, I001)
and `mypy --strict` (override, attr-defined, type-arg, unused-ignore) configuration.
Deviations were made in favor of the explicit "clean" requirement while preserving the
public API and runtime behavior 1:1:

1. **`tools/mock_ida.py` modified (the load-bearing fix).** The brief assumed
   "Qt attributes work with the mock", but `QtCore.QAbstractTableModel` cannot be
   subclassed from a `MagicMock`-backed `PySide6` — the subclass's own Python methods
   (`rowCount`, `data`, etc.) get shadowed by the mock, so `m.rowCount()` returned a
   MagicMock instead of calling the user's implementation. Fix: `install()` now skips
   mocking `PySide6`/`PyQt5` when they are genuinely importable, and falls back to the
   mock only when absent. `reset()` was already safe via its `isinstance(attr, MagicMock)`
   guard. This is backward compatible — environments without real Qt still get the mock.

2. **Removed unused `import idaapi`** from `structure_model.py` (F401).

3. **`B008` mutable default argument**: hoisted `QtCore.QModelIndex()` into a
   module-level singleton `_INVALID_INDEX` used as the default for `parent`.

4. **`N802` (Qt camelCase)**: added targeted `# noqa: N802` on the Qt-mandated method
   names (`rowCount`, `columnCount`, `headerData`, `data`, `beginResetModel`,
   `endResetModel`). These names are fixed by the Qt C++ API and cannot be renamed.

5. **mypy `[override]` Liskov**: widened `parent`/`index` parameter types from
   `QModelIndex` to `QModelIndex | QPersistentModelIndex` to match the supertype stub.

6. **mypy Qt enums**: used the fully-qualified enum paths
   (`QtCore.Qt.ItemDataRole.DisplayRole`, `QtCore.Qt.Orientation.Horizontal`) which
   mypy resolves correctly under PySide6 6.11 stubs (the short `QtCore.Qt.DisplayRole`
   form triggers `[attr-defined]`).

7. **`list[Any]` type args**: parameterized bare `list` to satisfy `type-arg`.

8. **Test file**: removed unused `pytest` import, sorted imports, used the
   fully-qualified Qt enum paths in assertions. Behavior identical.

The public surface (`StructureModel`, `HEADERS`, `rowCount`, `columnCount`,
`headerData`, `data`, `add_row`, `clear`, `items`) is unchanged from the brief.

## Files Changed

- `src/hexrays_pytools/domain/recon/structure_model.py` (new)
- `tests/domain/recon/test_structure_model.py` (new)
- `tools/mock_ida.py` (modified — Qt modules now skipped when real Qt is importable)

## Commit

See git log for SHA and subject.

## Notes for Task 2.15 (Phase 2 Gate)

- `StructureModel` is the Qt model half of the builder; `ReconWorkspace`
  (`workspace.py`) already has a `model` slot typed as `object | None` waiting for
  Phase 2 wiring — that can now be tightened to `StructureModel | None`.
- The `mock_ida.py` change is environment-aware: CI without PySide6 installed will
  still get the MagicMock (tests that subclass `QAbstractTableModel` would then fail
  there). If CI lacks PySide6, either install it in the dev extras or restrict
  `test_structure_model.py` to environments where PySide6 is importable.
