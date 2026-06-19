# Task 3.3 Report: domain/browser/tree_model.py

## Status: DONE

## Deliverables
1. `src/hexrays_pytools/domain/browser/tree_model.py` — `TreeItem` dataclass + `TreeModel(QtCore.QAbstractItemModel)`.
2. `tests/domain/browser/test_tree_model.py` — 5 tests, verbatim body from the brief (imports sorted by ruff).

## TDD Summary
- **RED**: test module failed to import (`ModuleNotFoundError: ...tree_model`) before the source existed.
- **GREEN**: 5/5 pass after implementation.
  - `test_tree_item_init`
  - `test_tree_item_append_child`
  - `test_tree_model_init_empty` (rowCount=0, columnCount=3)
  - `test_tree_model_header` (Name / Declaration / Address)
  - `test_has_function_match_with_re` (B2 fix: stdlib `re.search`)
- **Gates**:
  - `pytest`: 5 passed (QT_QPA_PLATFORM=offscreen, PYTHONPATH=src).
  - `ruff check`: All checks passed.
  - `mypy --strict`: Success, no issues.

## B2 Fix (carried over)
`has_function_match` uses stdlib `re.search` instead of the Qt5-only `QRegExp.indexIn` (removed in Qt6 / PySide6).

## Deviations from the verbatim brief
The brief's verbatim source triggered 16 mypy/ruff errors under the project's strict config. I rewrote the source to match the conventions already established by the sibling `src/hexrays_pytools/domain/recon/structure_model.py`:

| Brief verbatim | This commit | Reason |
|----------------|-------------|--------|
| `from .registered_vtable import RegisteredVTable, VirtualMethod` | dropped (only `Class` used) | ruff F401 unused import |
| `parent: "TreeItem \| None"`, `child: "TreeItem"`, `-> "TreeItem \| None"` | unquoted (`from __future__ import annotations` already present) | ruff UP037 |
| `children: list`, `_classes: dict` | `list[TreeItem]`, `dict[str, Class]` | mypy type-arg |
| `QtCore.QModelIndex()` as default arg | module-level `_INVALID_INDEX` sentinel | ruff B008 |
| `role: int = QtCore.Qt.DisplayRole`, `orientation == QtCore.Qt.Horizontal` | `QtCore.Qt.ItemDataRole.DisplayRole`, `QtCore.Qt.Orientation.Horizontal` | mypy attr-defined (PySide6 stubs only expose the enum-class paths) |
| `rowCount`/`columnCount`/`headerData`/`data`/`index`/`setupModelData` bare | `# noqa: N802 - Qt API override` | ruff N802 (Qt-mandated camelCase API) |
| `for offset, vtable in ...` | `for _offset, vtable in ...` | ruff B007 unused loop var |
| `def parent(self, index)` bare | `def parent(...) -> ...: # type: ignore[override]` + positional-only `index, /` | mypy override — PySide6 stubs overload `QObject.parent() -> QObject` and `QAbstractItemModel.parent(index) -> QModelIndex`; a single Python override cannot satisfy both. This is a known PySide6 stub limitation, not a real Liskov violation; the legacy `refs/HexRaysPyTools/HexRaysPyTools/core/classes.py:494` has the identical signature. Consistent with the project's existing `# type: ignore[misc]` treatment of idaapi multiple-inheritance stub limits. |
| `index.internalPointer()` returned unchecked | `isinstance(ptr, TreeItem)` guard, fallback to root | mypy no-any-return |

### Test file deviations
The brief's test body is byte-for-byte verbatim. The only change is import ordering: ruff `I001` flagged the unsorted imports (`from unittest.mock import MagicMock` before `from hexrays_pytools...`), so ruff's `--fix` reordered them. The test assertions are unchanged. The test calls `m.headerData(0, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)` (shorthand) against an implementation that uses `QtCore.Qt.Orientation.Horizontal` internally — this works because the PySide6 enums are equal at runtime (`QtCore.Qt.Horizontal is QtCore.Qt.Orientation.Horizontal`).

## Verification commands
```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=src pytest tests/domain/browser/test_tree_model.py -v --no-cov
python -m ruff check src/hexrays_pytools/domain/browser/tree_model.py tests/domain/browser/test_tree_model.py
PYTHONPATH=src python -m mypy --strict src/hexrays_pytools/domain/browser/tree_model.py
```
All three pass.

## Commit
```
feat(browser): add TreeModel (B2 fix: QRegExp.indexIn → re.search)
```
SHA recorded in the final report-back message.

## Notes for Task 3.4 (proxy_model)
- `TreeModel` exposes `_classes: dict[str, Class]` for the proxy/filter to read.
- `has_function_match(class_name, name_regex)` is wired for the proxy's filter acceptance logic.
- `setupModelData` resets `_classes` and rebuilds the tree from Local Types via `Class.create`.
