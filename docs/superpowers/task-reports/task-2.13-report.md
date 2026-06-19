# Task 2.13 Report: domain/til/type_library.py

## Status: DONE_WITH_CONCERNS

Status is DONE_WITH_CONCERNS rather than plain DONE because two minimal
deviations from the brief's verbatim source were required to clear the
project's `mypy --strict` and `ruff` gates, and one test (provided verbatim
in the brief) contained a `unittest.mock` namespace bug that would never
pass. All deviations are documented below with rationale. Functionality is
unchanged from the brief's intent; all 5 tests pass and every quality gate
is green.

## Commit

- **SHA:** `9faa39b`
- **Subject:** `feat(til): add type_library (no ctypes FFI; graceful fallback for IDA 9.x)`
- **Files changed:** 6 files, 175 insertions

## Deliverables

| File | Purpose |
|------|---------|
| `src/hexrays_pytools/domain/til/__init__.py` | empty package marker |
| `src/hexrays_pytools/domain/til/type_library.py` | `choose_til`, `create_type`, `import_type` — TIL picker and type import helpers; uses `idaapi.enable_numbered_types` if present, else logs and degrades |
| `tests/domain/til/__init__.py` | empty package marker |
| `tests/domain/til/test_type_library.py` | 5 unit tests |
| `src/hexrays_pytools/ui/__init__.py` | empty package marker (stub, planned for Task 3.5) |
| `src/hexrays_pytools/ui/chooser.py` | `MyChoose` stub — minimal `idaapi.Choose` subclass with `OnClose`/`OnGetLine`/`OnGetSize` (stub, planned for Task 3.5) |

## TDD Summary

| Phase | Result |
|-------|--------|
| RED | `ModuleNotFoundError: No module named 'hexrays_pytools.domain.til.type_library'` (collection error, tests cannot import) |
| GREEN (first attempt) | 4/5 pass; 5th failed due to brief's mock namespace bug (see Deviation #3) |
| GREEN (final) | 5/5 tests pass |

### Tests

1. `test_create_type_succeeds_for_new_type` — `create_type` returns True for a new name (existence check False, verify True)
2. `test_create_type_fails_if_already_exists` — `create_type` returns False when the name already exists
3. `test_import_type_returns_ordinal_on_success` — `import_type` returns the new ordinal (42) when `idc.import_type` succeeds
4. `test_import_type_returns_none_on_failure` — `import_type` returns None when `idc.import_type` returns BADORD
5. `test_choose_til_returns_none_on_cancel` — `choose_til` returns None when the chooser's `Show()` returns -1

### Quality Gates

| Gate | Result |
|------|--------|
| `pytest tests/domain/til/test_type_library.py -v` | 5 passed |
| `mypy --strict` on `type_library.py` | Success: no issues found |
| `mypy --strict` on `chooser.py` (stub) | Success: no issues found |
| `mypy --strict` on `domain/til/` + `ui/` (4 files) | Success: no issues found in 4 source files |
| `ruff check` on `domain/til/` + `ui/` + `tests/domain/til/` | All checks passed! |
| Full project suite (regression) | 89 passed, coverage 81.63% (gate: 80%) |

## Deviations from Brief

The brief's verbatim content had three issues that prevented the strict
quality gates from being clean. Each was resolved with a minimal,
intent-preserving change.

### 1. Bare `tuple` annotation fails mypy `--strict` (`[type-arg]`)

The brief's `def choose_til() -> tuple | None` triggers mypy's
`[type-arg]` rule under `strict = true` (bare `tuple` is a generic-type
argument error). Tightened to `tuple[Any, ...] | None` (added
`from typing import Any`). Runtime behavior is unchanged; the return value
is the heterogeneous `(til_t, max_ordinal, is_local)` and the brief
deliberately left it untyped. Same fix pattern as Task 2.11's report.

### 2. Unannotated `library` parameter fails mypy `--strict` (`[no-untyped-def]`)

The brief's `def import_type(library, name: str) -> int | None` triggers
`[no-untyped-def]` for the untyped `library` arg. Annotated as
`library: Any` — the parameter is an opaque `til_t*` SWIG handle with no
Python-side type, and `Any` accurately reflects that intent without
introducing a false precision the brief did not call for.

### 3. Brief's `test_choose_til_returns_none_on_cancel` patches the wrong namespace (would never pass)

The brief's 5th test patches `hexrays_pytools.ui.chooser.MyChoose`, but
`type_library.py` binds the name into its own module namespace via
`from ...ui.chooser import MyChoose`. Per the `unittest.mock` documentation
("patch the namespace where it is looked up"), patching `ui.chooser.MyChoose`
has **no effect** on the `MyChoose` that `choose_til()` actually calls — the
unpatched real `MyChoose` runs against the mock_ida infrastructure, returns a
non-`-1` pick, and the test fails with:

```
AssertionError: assert (<MagicMock ... 'ida._MockIdaModule.get_idati().base()'>, 1, False) is None
```

This is not a test flakiness or environment issue — the brief's test as
written cannot pass against the brief's implementation. Fixed by changing
the patch target from `chooser_mod.MyChoose` to `tl_mod.MyChoose` (i.e.
patching `hexrays_pytools.domain.til.type_library.MyChoose`, the namespace
where `choose_til` actually resolves the name). Added a comment citing the
`unittest.mock` docs so the reasoning is explicit.

### 4. Brief's test variable `MockChoose` fails ruff `N806`

The brief's `with patch.object(...) as MockChoose:` triggers ruff's `N806`
rule ("variable in function should be lowercase"). This is ruff not
recognizing context-manager `as` binding as a conventional exception.
Renamed to `mock_choose` (lowercase). Functionally identical.

### Additional: `MyChoose` stub typed for `--strict`

The brief's stub code block was given without type annotations, which fails
`mypy --strict` (`[type-arg]` on bare `list`, `[no-any-return]` on the
`OnGetLine` return). Annotated the stub's parameters/returns with
`list[Any]` and `Any` to match the project's strict config. The class body
is otherwise byte-identical to the brief's snippet.

## Notes

- **Mock infrastructure interaction:** `idaapi.get_idati()` returns a
  `MagicMock` in the mock_ida fixture; `idati.nbases` is therefore a
  `MagicMock` that is falsy-ish under `range()`. In practice `range()` on a
  `MagicMock` raises `TypeError` at runtime, which is why the 5th test must
  mock `MyChoose` (and does so correctly after Deviation #3) — without the
  mock the loop body never reaches the `Show()` call in the test context.

- **Commit convention:** Per the established Task 2.x convention (see
  `62ce9e8`), only `src/` and `tests/` files are committed. The brief and
  this report remain as untracked working artifacts under
  `docs/superpowers/task-reports/`, matching how all prior phase reports are
  handled in this repo.

- **`chooser.py` stub ownership:** The stub lives under `src/hexrays_pytools/ui/`
  and is tagged in its docstring as a placeholder for Task 3.5. When 3.5
  lands, the stub can be replaced wholesale; `type_library.py` imports only
  `MyChoose` by name, so the public surface is stable.

## Verification Commands

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/til/test_type_library.py -v
python -m mypy --strict src/hexrays_pytools/domain/til/type_library.py
python -m mypy --strict src/hexrays_pytools/ui/chooser.py
python -m ruff check src/hexrays_pytools/domain/til/ src/hexrays_pytools/ui/ tests/domain/til/
PYTHONPATH=src pytest  # full suite + coverage gate
```
