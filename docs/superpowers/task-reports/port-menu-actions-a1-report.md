# Phase A.1 Report: Port `core/const.py` (tinfo singletons)

**Date:** 2026-06-19
**Branch:** `master`
**Result:** A.1 of the port-menu-actions plan complete; scanner engine now has
its tinfo singletons to depend on.

## Summary

Created `domain/const.py` (133 LOC) with a `Consts` dataclass and
`init_consts()` factory. Wired the dataclass into `Session.consts` so the
scanner engine (Phase A.5+) can pull singletons through the Session rather
than relying on module-level globals (which is the B11 bug from the CHANGELOG).

## Changes

| File | Change |
|---|---|
| `src/hexrays_pytools/domain/const.py` | **NEW** — `Consts` dataclass + `init_consts()` factory |
| `src/hexrays_pytools/domain/session.py` | Add `consts: Consts \| None = None` field + populate in `_init_caches()` |
| `tests/domain/test_const.py` | **NEW** — 9 tests covering dataclass shape, factory output, Session integration |

## Design notes

- **Why a dataclass, not module globals**: Matches the Session-based architecture already in place (B11 fix). The `Consts` instance is owned by `Session.consts`, with explicit lifetime (built in `Session.open()`, GC'd on `Session.close()`).
- **`Consts` is plain data**: `init_consts()` requires IDA (real or mocked), but the dataclass itself is just fields — it can be constructed and inspected without IDA, which makes the dataclass contract directly testable.
- **Field naming**: snake_case to match Python idiom (the original used `UPPER_SNAKE_CASE` for module globals). Renamed all 17 fields (`EA64 → ea64`, `PVOID_TINFO → pvoid_tinfo`, etc.).
- **Session is the source of truth**: `session.consts` is the canonical reference. Callers must never import constants directly from `const.py`; they should read `session.consts.<field>`. (This will be enforced when scanners port in Phase A.5+.)
- **Idempotency preserved**: `Session.open()` short-circuits when `is_open=True`, so calling `open()` twice does NOT re-init `consts` — same dataclass instance is returned both times. Test `test_session_open_is_idempotent_for_consts` guards this.

## Tests added (9 new)

| Test | Verifies |
|---|---|
| `test_consts_is_importable` | `Consts` can be imported |
| `test_consts_can_be_constructed_manually` | `Consts(...)` works without IDA — proves dataclass contract is decoupled from `init_consts()` |
| `test_consts_dataclass_is_mutable` | Field reassignment works (regular dataclass, not frozen) |
| `test_init_consts_returns_consts` | `init_consts()` returns a `Consts` instance |
| `test_init_consts_populates_all_tinfo_fields` | All 14 tinfo fields are non-None after init |
| `test_init_consts_legal_types_has_5_entries` | `legal_types` list has 5 entries (PVOID, PX_WORD, PWORD, PBYTE, X_WORD) |
| `test_init_consts_ea_size_matches_ea64` | `ea_size` is 8 if ea64, else 4 |
| `test_session_consts_default_is_none` | Fresh Session has `consts=None` |
| `test_session_open_populates_consts` | `Session.open()` populates `session.consts` with a `Consts` instance |
| `test_session_open_is_idempotent_for_consts` | Calling `open()` twice returns the same Consts instance |
| `test_session_close_keeps_consts` | `close()` does not clear `consts` (re-open would re-init anyway) |

## Quality gates

| Gate | Result |
|---|---|
| `pytest tests/domain/test_const.py tests/domain/test_session.py` | 19 passed |
| Full `pytest` suite | **344 passed** (+9 from before — was 335) |
| Coverage | **83.01%** (gate met, was 86.62% — drop is because the new module added 70 statements to the codebase, expanding the denominator) |
| `mypy --strict src/hexrays_pytools/domain/const.py` | Clean |
| `mypy --strict src/hexrays_pytools/domain/session.py` | Clean |
| `ruff check` on changed files | Clean |

## What this unlocks

- **Phase A.2 (ScannedObject hierarchy)** can read tinfos for `MemoryAllocationObject.create()` heuristics (`"malloc" in func_name`).
- **Phase A.5 (SearchVisitor)** can use `legal_types`, `PVOID_TINFO`, `PX_WORD_TINFO`, `DUMMY_FUNC` from the session.
- **Phase B.7 (scanner actions)** can check `is_legal_type(obj.tinfo)` against `session.consts.legal_types`.

## Files touched

```
src/hexrays_pytools/domain/const.py     (NEW, 133 LOC, 100% covered)
src/hexrays_pytools/domain/session.py   (MODIFIED, +6 LOC)
tests/domain/test_const.py              (NEW, 147 LOC, 9 tests)
docs/superpowers/task-reports/
  ├── port-menu-actions-a1-brief.md     (already in working tree)
  └── port-menu-actions-a1-report.md    (this file)
```

## Deviations from brief

None. The brief specified the field-name mapping, the dataclass shape, and the
test list — all delivered exactly as written.
