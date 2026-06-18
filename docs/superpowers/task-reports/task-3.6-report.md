# Task 3.6 Report: ui/widgets (3 forms)

- **Status:** DONE_WITH_CONCERNS
- **Commit:** `69ad2534d894bb297842cee4f3f22d4334b20c6d`
  `feat(ui): add 3 widgets (StructureBuilder, ClassViewer, GraphViewer) — B1 fix: FormToPySideWidget`
- **Brief:** `docs/superpowers/task-reports/task-3.6-brief.md`

## Files

| File | Path | Notes |
|------|------|-------|
| Impl | `src/hexrays_pytools/ui/widgets/__init__.py` | empty |
| Impl | `src/hexrays_pytools/ui/widgets/structure_builder.py` | `StructureBuilder(idaapi.PluginForm)` — B1 fix (FormToPySideWidget → PySide6) |
| Impl | `src/hexrays_pytools/ui/widgets/class_viewer.py` | `ClassViewer(idaapi.PluginForm)` — B1 fix |
| Impl | `src/hexrays_pytools/ui/widgets/graph_viewer.py` | `StructureGraphViewer(idaapi.GraphViewer)` |
| Test | `tests/ui/__init__.py` | empty |
| Test | `tests/ui/widgets/__init__.py` | empty |
| Test | `tests/ui/widgets/test_structure_builder.py` | smoke init |
| Test | `tests/ui/widgets/test_class_viewer.py` | smoke init |
| Test | `tests/ui/widgets/test_graph_viewer.py` | smoke init |
| Infra | `tools/mock_ida.py` | added real `PluginForm`, `GraphViewer`, `Choose` base classes (see Deviation 1) |

## TDD Summary

- **RED:** All 3 tests failed before the mock_ida fix. `StructureBuilder(model)` returned a bare
  `MagicMock` (not an instance whose `__init__` ran), so `sb.structure_model is model` failed with
  `AssertionError: assert <MagicMock ...> is <MagicMock ...>`. Same shape for `ClassViewer` and
  `StructureGraphViewer`. Confirmed the failure mode before any green-phase work.
- **GREEN:** All 3 pass after adding real base classes to `mock_ida` (Deviation 1).
- **mypy --strict:** clean (0 errors) on `src/hexrays_pytools/ui/` (6 source files).
- **ruff check:** clean on `src/hexrays_pytools/ui/` + `tests/ui/`.
- **Env:** `QT_QPA_PLATFORM=offscreen`, `PYTHONPATH=src`, Python 3.14.5, PySide6 6.11.1 installed locally.

```
3 passed in 0.14s   (tests/ui/)
0 mypy errors       (src/hexrays_pytools/ui/)
All ruff checks passed
```

## Deviations from brief

The widget sources were implemented verbatim from the brief, with the surgical fixes below
required to satisfy the strict gates. None change the public API or runtime behavior.

### 1. `tools/mock_ida.py`: added real `PluginForm`, `GraphViewer`, `Choose` base classes (reason for DONE_WITH_CONCERNS)

The brief says "Both PluginForm and GraphViewer base classes are in mock_ida" and the tests
instantiate the widgets and assert on attributes (`sb.structure_model is model`). This cannot
work with `mock_ida` as it stood: `idaapi.PluginForm` resolved to a `MagicMock` (catch-all
`__getattr__`). When Python builds `class StructureBuilder(idaapi.PluginForm)` with a
`MagicMock` base, the resulting class is itself a `MagicMock`, so `StructureBuilder(model)`
returns a mock instance whose `__init__` never runs — `sb.structure_model` becomes a fresh
mock attribute, not `model`.

This is the exact same problem Task 1.6 hit with `idaapi.plugin_t` (report:
`task-1.6-report.md`) and Task 2.4 hit with `idaapi.ctree_parentee_t` (report:
`task-2.4-report.md`). The established fix is to add real `object`-subclassing base classes
as class attributes on `_MockIdaModule`, which shadow the catch-all and let
`class X(idaapi.PluginForm)` define a genuine class.

Added three bases:

- **`PluginForm`** — plain class (empty body). The real `FormToPySideWidget` is a staticmethod
  that tests patch at the class level, so no implementation is needed.
- **`GraphViewer`** — has working `__init__(title)`, `Clear`, `AddNode` (returns node id),
  `AddEdge`, `Refresh`, and `__getitem__` stubs so `OnRefresh`/`OnGetText` can be exercised
  without IDA. The production `StructureGraphViewer` calls all of these.
- **`Choose`** — plain class with `CH_MODAL` and `CHCOL_PLAIN` constants (referenced by
  `ui/chooser.py` and `domain/til/type_library.py`) plus a simple `__init__(title, cols, **kwargs)`.

Without the `Choose` base, `domain/til/type_library.py:36` (`10 | idaapi.Choose.CHCOL_PLAIN`)
raises `AttributeError: type object 'Choose' has no attribute 'CHCOL_PLAIN'` because the real
class lacks the constant the previous mock-on-demand provided. Added both constants.

### 2. mypy/ruff cleanups on the impl (verbatim source)

The brief's verbatim source produced 7 mypy errors and 2 ruff error classes under the project's
strict config. Same precedent as Task 3.4 (`task-3.4-report.md` §3). Runtime behavior is identical.

- **Removed** unused `QtCore` from `from PySide6 import QtCore, QtWidgets` in
  `structure_builder.py` and `class_viewer.py` (neither uses `QtCore`). This also dropped the
  now-unused `# type: ignore[import-not-found]` (PySide6 ships stubs; the ignore was flagged as
  unused by mypy).
- **Reformatted** the import blocks (blank line between stdlib and third-party groups) in all
  three widget files to satisfy ruff `I001`.
- **Guarded** `self.parent.setLayout(...)` with `assert self.parent is not None` in both
  `StructureBuilder._init_ui` and `ClassViewer._init_ui` (parent is assigned in `OnCreate`
  immediately before `_init_ui`, so the assert is always true at runtime) to satisfy mypy
  `union-attr` on `QWidget | None`.
- **Wrapped** the return of `idaapi.PluginForm.FormToPySideWidget(form)` in both
  `FormToPySideWidget` staticmethods with an explicit `widget: QtWidgets.QWidget = ...` binding
  to satisfy mypy `no-any-return`.
- **Wrapped** `return node.tooltip()` with `str(...)` in `GraphViewer.OnHint` to satisfy
  `no-any-return` (`node` is `Any` from `__getitem__`).

### 3. ruff I001 fix on test files

The brief's test files had `import os` immediately followed by `os.environ.setdefault(...)`.
Because the production import lives inside the test function (not at module level, unlike the
browser tests), ruff/isort saw a malformed import block. Applied `ruff --fix` to insert the
expected blank line after `import os`. Functionally identical (the env var is still set before
any Qt import); only whitespace changed.

## B1 fix verified

The B1 fix (the reason this task exists) is in place: both `StructureBuilder.FormToPySideWidget`
and `ClassViewer.FormToPySideWidget` call `idaapi.PluginForm.FormToPySideWidget(form)` — the
PySide6 variant — never the removed PyQt5 `FormToPyQtWidget`.

## Concerns

1. **Global coverage gate at 74.71% (below 80%).** The three widget files have heavy UI methods
   (`OnCreate`, `_init_ui`, `FormToPySideWidget`, `OnRefresh`, `OnGetText`, `OnHint`,
   `OnDblClick`) that require a running IDA + Qt event loop to exercise; they cannot be
   meaningfully unit-tested. Module coverage: `structure_builder.py` 48%, `class_viewer.py` 48%,
   `graph_viewer.py` 34%. The brief specifies minimal smoke tests (init only) by design. This is
   the same "structural coverage concern" pattern documented in Task 0.3
   ("deferred to Task 0.9") and Task 0.9. The per-task gate is expected to fail on UI widget
   tasks; the **phase gate (Task 3.7)** owns the 80% threshold and may need to either add
   integration-style tests or accept the UI structural gap, mirroring how Phase 0 handled
   `logging_setup.py`. All non-UI code remains well above 80%.

2. **mock_ida.py modified outside the brief's file list.** The brief listed 5 files (3 widgets +
   2 widget `__init__`) but its premise ("PluginForm and GraphViewer base classes are in
   mock_ida") was not yet true. The mock_ida change is the established fix (Tasks 1.6, 2.4) and
   is required for the brief's own tests to pass. Flagged as a concern because it's an extra file
   in the commit.

## Gate verification commands

```bash
# Brief's specified verification (all pass clean):
QT_QPA_PLATFORM=offscreen PYTHONPATH=src pytest tests/ui/ -v --no-cov
# -> 3 passed

python -m mypy --strict src/hexrays_pytools/ui/
# -> Success: no issues found in 6 source files

python -m ruff check src/hexrays_pytools/ui/ tests/ui/
# -> All checks passed!

# Full suite (no regressions; gate note above):
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m pytest tests/ --no-cov
# -> 146 passed (was 143 before this task: +3 widget tests)

# Modified infra file also clean:
python -m mypy --strict tools/mock_ida.py   # -> 0 errors
python -m ruff check tools/mock_ida.py      # -> All checks passed!
```
