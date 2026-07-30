# Logger Fix + Parity Test Expansion Design

**Date:** 2026-07-30
**Status:** Approved (verbal)
**Supersedes:** none
**Related:** `docs/superpowers/specs/2026-07-07-hexrays-pytools-ng-fork-design.md`

## Context

The HexRaysPyTools-ng v2.0.0 rewrite passed all quality gates (532 unit
tests, 83.67% coverage, mypy --strict clean, ruff clean) and the 5-path
`verify_parity.py` script previously confirmed 5/5 PASS on IDA 9.4.
However, two gaps surfaced during the 2026-07-30 audit:

1. **Logger is half-wired.** `setup_logging()` is defined in
   `logging_setup.py` but never called from `plugin.py:init()`. The
   CLAUDE.md "Logging & debug scanner" section documents a working
   `IdaOutputHandler` that emits to the IDA Output window with a
   `[HexRaysPyTools]` prefix — neither the handler nor the prefix
   exists in code. As a result, `hcli plugin config ... log_level DEBUG`
   sets a setting that is never honored; all `logger.debug(...)` trace
   statements in the scanner/rename/swap-if modules are silent.

2. **Parity test coverage is shallow.** `verify_parity.py` exercises
   only `Member` and `StructureModel` paths. Four other path groups that
   the coverage gate omits (because `mock_ida` cannot reproduce
   `ctree_parentee_t` dispatch) have **no** end-to-end guard:
   - Scanner visitors (`visitor_base.py`, `member_extractor.py`)
   - ctree rename engine (`ctree/rename.py`)
   - Swap-if engine (`ctree/swap_if.py`)
   - Negative-offset / CONTAINING_RECORD engine (`ctree/negative_offsets.py`)

The commit `9f8060b` already proved the value of E2E parity testing:
the `verify_parity.py` script caught two bugs (`_BYTE void;` cdecl
reject, `idaapi.BT_BYTE` missing) that all 532 unit tests missed
because the mock satisfies the missing attribute.

This design addresses both gaps in one cycle: the logger fix is the
debugging prerequisite for the parity test expansion (when a new path
fails, DEBUG trace is the only way to see which `_manipulate` branch
fired).

## Non-Goals

- Rewriting or extending the scanner/rename/swap-if/negative-offset
  logic itself. These modules are out of scope — we are adding test
  coverage, not fixing behavior (unless a parity test reveals a bug, in
  which case that bug becomes a follow-up task).
- Negative-offset **action** wiring (the `SelectContainingStructure`
  right-click action). The visitor classes and `collect_potential_negatives`
  are tested; the action that triggers `_parse_magic_comment` on a live
  lvar is left for a later cycle.
- CI integration. The parity test runs headless on a developer machine
  with IDA 9.4; automating it in CI requires an IDA license in the
  runner, which is out of scope.

## Part 1 — Logger Fix

### Problem

Three concrete defects, all in or around `logging_setup.py`:

| # | Defect | Evidence |
|---|---|---|
| 1.1 | `setup_logging()` never called | `plugin.py:init()` (lines 63-116) has no `setup_logging` call; `grep setup_logging src/hexrays_pytools/plugin.py` returns nothing |
| 1.2 | No `IdaOutputHandler` | `logging_setup.py:19-22` only adds a `StreamHandler`; grep for `IdaOutputHandler` in `src/` returns nothing |
| 1.3 | Format missing `[HexRaysPyTools]` prefix | `_LOG_FORMAT = "[%(levelname)s] %(message)s\t(%(module)s:%(funcName)s)"` — CLAUDE.md says prefix exists |

Net effect: `log_level=DEBUG` is a no-op. Scanner DEBUG trace (the
primary diagnostic for "why did my scan miss field X?") is invisible.

### Solution

#### File: `src/hexrays_pytools/logging_setup.py` (rewrite)

Replace the current 23-line module with a context-aware version:

```python
"""Centralized logging configuration for HexRaysPyTools.

Configures the root logger to emit either to the IDA Output window
(when running inside IDA, via `idaapi.msg`) or to stderr (when running
in the mock/test environment). Called once during plugin init via
`setup_logging(session.log_level)`.
"""
from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "[HexRaysPyTools][%(levelname)s] %(message)s (%(module)s:%(funcName)s:%(lineno)d)"


class IdaOutputHandler(logging.Handler):
    """Emit log records to the IDA Output window via `idaapi.msg`.

    Used when the plugin runs inside IDA. In the mock/test environment
    `idaapi.msg` does not exist (or is a Mock), so the fallback
    StreamHandler is used instead — see `_make_handler`.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            import idaapi  # type: ignore[import-not-found]

            idaapi.msg(self.format(record) + "\n")
        except Exception:
            # If idaapi.msg fails (e.g., IDA shutting down), fall back
            # to stderr rather than crashing the plugin.
            sys.stderr.write(self.format(record) + "\n")


def _ida_output_available() -> bool:
    """Return True if we are running inside real IDA (not the mock).

    The mock's `idaapi.msg` is a Mock callable; the real one is a
    builtin function. We detect the real one by checking that the
    `idaapi` module is importable and `msg` is not a Mock instance.
    """
    try:
        import idaapi  # type: ignore[import-not-found]
        from unittest.mock import Mock

        return callable(idaapi.msg) and not isinstance(idaapi.msg, Mock)
    except ImportError:
        return False


def _make_handler() -> logging.Handler:
    """Return the appropriate handler for the current environment."""
    if _ida_output_available():
        return IdaOutputHandler()
    return logging.StreamHandler()


def setup_logging(level: int) -> None:
    """Configure the root logger. Idempotent.

    Removes any previously-installed HexRaysPyTools handlers before
    adding a fresh one — so re-calling `setup_logging` (e.g., after a
    `log_level` setting change + plugin reload) does not stack handlers.
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Remove our previous handlers to avoid duplicates on re-init.
    for h in list(root.handlers):
        if getattr(h, "_hexrays_pytools", False):
            root.removeHandler(h)

    handler = _make_handler()
    handler._hexrays_pytools = True  # type: ignore[attr-defined]
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(handler)
```

Design decisions:
- **Marker attribute `_hexrays_pytools`** on the handler: this is how
  `setup_logging` identifies "our" handler for idempotent removal. The
  alternative (remove ALL handlers) would clobber handlers installed by
  other plugins or by IDA itself.
- **Lazy `import idaapi` inside `emit`**: keeps `logging_setup.py`
  importable from pure-Python test contexts where `idaapi` is absent.
- **`_ida_output_available()` uses `isinstance(idaapi.msg, Mock)`**: the
  `tools/mock_ida.py` mock installs `Mock()` callables for missing
  functions. In real IDA, `idaapi.msg` is a SWIG builtin function. This
  is the most reliable way to distinguish the two environments without
  reaching into `sys.modules['_main_']` or checking IDA version globals.

#### File: `src/hexrays_pytools/plugin.py` (1-line addition)

Insert one call in `init()`, after `session.open()` (so `log_level` is
loaded from HCLI settings) and before `HxCallbackManager.install()` (so
callback-handler exceptions are logged from the start):

```python
def init(self) -> int:
    ...
    self.session = Session()
    self.session.open()
    setup_logging(self.session.log_level)   # ← ADD THIS LINE
    ...
```

Add `from .logging_setup import setup_logging` to the imports.

#### File: `tests/pure/test_logging_setup.py` (new)

Unit tests for the idempotency and handler selection logic. These run
under the existing pytest + mock_ida harness, so `idaapi.msg` is a Mock
→ `_ida_output_available()` returns False → `StreamHandler` is expected.

- `test_setup_logging_idempotent_no_duplicate_handlers`
- `test_setup_logging_sets_root_level`
- `test_format_has_hexrays_prefix`
- `test_format_has_levelname_and_module`
- `test_fallback_stream_handler_when_mock` (assert `_make_handler()`
  returns `StreamHandler` under mock)
- `test_ida_output_handler_falls_to_stderr_on_failure` (mock
  `idaapi.msg` to raise, assert `sys.stderr.write` is called)

### Impact

- **IDA real environment:** Output window shows
  `[HexRaysPyTools][DEBUG] ShallowScanVariable: start func=...` when
  `log_level=DEBUG`. Matches CLAUDE.md's documented behavior.
- **Test/mock environment:** `StreamHandler` (unchanged from today);
  the `isinstance(idaapi.msg, Mock)` check prevents a `Mock` from being
  mistaken for a real `idaapi.msg`.
- **Coverage:** `logging_setup.py` rises from 67% to ~90%+ (the only
  uncovered path will be `IdaOutputHandler.emit`'s real-IDA branch,
  which cannot run under mock).

## Part 2 — Parity Test Expansion

### Architecture

```
verification/
├── test_patterns.c          # NEW: C source for test target
├── test_patterns.exe        # compiled binary (gitignored)
├── test_patterns.exe.i64    # IDA database (gitignored)
├── verify_parity.py         # EXTENDED: +10 test functions
├── logs/                    # gitignored
│   ├── parity_results.json  # structured test output
│   └── parity.log           # IDA log capture
└── .gitignore               # NEW: ignore *.exe, *.i64, logs/, .id0/.id1/.id2/.nam
```

The root `.gitignore` already covers `__pycache__/`, `dist/`, `*.egg-info/`.
The new `verification/.gitignore` adds the IDA-specific artifacts
(`*.exe`, `*.i64`, `*.id0`, `*.id1`, `*.id2`, `*.nam`, `logs/`). A
verification-local `.gitignore` is preferred over polluting the root
file because the patterns are specific to the verification workflow.

### Test Target — `test_patterns.c`

A single C file compiled with GCC `-O0 -g` to produce
`test_patterns.exe`. Five `__attribute__((noinline))` functions, each
containing the pattern for one or more test groups:

```c
#include <stdint.h>
#include <stdlib.h>

/* anti-dead-code sink: defined here (not just `extern`) so the linker
   has a symbol to resolve. `volatile` forces every read/write to hit
   memory, defeating any residual optimizer cleverness at -O0. */
volatile int g_sink = 0;

/* --- Group 1: Scanner (struct pointer field access) --- */
struct ScanTarget {
    int   field_a;            /* offset 0 */
    int   field_b;            /* offset 4 */
    void* field_c;            /* offset 8 */
};

__attribute__((noinline))
void scan_simple(struct ScanTarget* p) {
    p->field_a = 1;
    p->field_b = p->field_a + 1;
    g_sink = p->field_b;
}

__attribute__((noinline))
void scan_chain(struct ScanTarget* p) {
    struct ScanTarget* q = p;     /* assignment chain for ObjectDownwardsVisitor */
    q->field_a = 42;
    g_sink = q->field_a;
}

/* --- Group 2: Rename (assignment chains + call args) --- */
__attribute__((noinline))
void rename_assign_chain(int real_name, int a2) {
    int a1 = a2;                  /* RenameOther target: a1 ← a2 */
    g_sink = a1 + real_name;
}

__attribute__((noinline))
void callee_takes_arg(int meaningful) {
    g_sink = meaningful;
}

__attribute__((noinline))
void rename_call_arg(int real_value) {
    int a1 = real_value;
    callee_takes_arg(a1);         /* RenameOutside target: a1 ← "meaningful" */
}

/* --- Group 3: Swap-if (if/else + spaghetti) --- */
__attribute__((noinline))
int swap_if_else(int cond, int x, int y) {
    int result;
    if (cond > 0) {
        result = x + y;
    } else {
        result = x - y;
    }
    return result;
}

__attribute__((noinline))
int spaghetti_pattern(int cond, int x) {
    if (cond) {
        x = x * 2;
        x = x + 1;
    }
    return x;
}

/* --- Group 4: Negative offsets (CONTAINING_RECORD) --- */
struct Inner { int a; int b; };
struct Outer  { int header; char pad[4]; struct Inner inner; };  /* inner at offset 8 */

__attribute__((noinline))
void negative_offset_access(struct Inner* p) {
    p->a = 1;
    p->b = 2;
    g_sink = p->a;
}

/* --- main: force linker to keep all functions --- */
int main(void) {
    struct ScanTarget st = {0};
    scan_simple(&st);
    scan_chain(&st);
    rename_assign_chain(1, 2);
    rename_call_arg(3);
    g_sink = swap_if_else(1, 2, 3);
    g_sink = spaghetti_pattern(1, 4);
    struct Outer outer = {0};
    negative_offset_access(&outer.inner);
    return g_sink;
}
```

Design decisions:
- **GCC `-O0`**: The purpose is to verify the v2 port behaves like v1
  on clean, source-like Hex-Rays output. Real-world optimized code is a
  separate concern (Hex-Rays's job, not ours).
- **`__attribute__((noinline))` on every test function**: defense in
  depth. Even at `-O0`, GCC may still inline trivially small functions
  in some configurations; this attribute is the canonical guarantee.
- **`extern volatile int g_sink`**: prevents dead-code elimination of
  assignments. Every function writes to `g_sink` so the optimizer has
  no excuse to drop the writes.
- **Function names are ASCII identifiers** (`scan_simple`, not mangled
  C++): the parity test resolves functions by name via
  `idc.get_name_ea_simple("scan_simple")` (a thin wrapper over
  `ida_name.get_name_ea(BADADDR, name)`), which is stable across
  rebuilds regardless of compilation order.
- **No C++, no exceptions, no RTTI**: keeps the binary small and the
  Hex-Rays output clean (no name mangling, no vtable clutter).

### Parity Test Functions (10 new, extending `verify_parity.py`)

All new `t_xxx()` functions follow the existing `check(name, fn)` harness.
Each is listed below with its assertion contract. The existing 5 tests
(`t_get_udt_member`, `t_score`, `t_pack`, `t_set_decl`, `t_finalize`)
are unchanged.

#### Group 1 — Scanner (paths 6-7)

| # | Function | What it tests | Assertion contract |
|---|---|---|---|
| 6 | `t_scanner_shallow` | `NewShallowSearchVisitor.process()` on `scan_simple` | After `process()`, `model.items` (the public property — see `structure_model.py:211-213`; internal attr is `_items`) has ≥ 2 members; their offsets include 0 and 4. |
| 7 | `t_scanner_chain` | `NewShallowSearchVisitor` on `scan_chain` (assignment chain `q = p`) | After `process()`, `model.items` has ≥ 1 member at offset 0 (from `q->field_a`). Confirms `ObjectDownwardsVisitor` followed the `q = p` chain. |

Setup for both: construct a `ReconWorkspace`, `set_model(StructureModel())`,
resolve `scan_simple`/`scan_chain` by name, decompile, find the first
pointer-typed lvar as the scan seed, build a `VariableObject`, run the
visitor.

#### Group 2 — Rename engine (paths 8-9)

| # | Function | What it tests | Assertion contract |
|---|---|---|---|
| 8 | `t_rename_other` | `extract_rename_other_info` on `int a1 = a2;` in `rename_assign_chain` | Returns a `RenameOtherInfo` whose `.name == "a2"` and whose `.lvar.name` starts with `"a1"`. |
| 9 | `t_rename_outside` | `extract_rename_outside_info` on `callee_takes_arg(a1)` in `rename_call_arg` | Returns a `RenameOtherInfo` whose `.name == "meaningful"`. (RenameOutside reuses `RenameOtherInfo`.) |

Setup for both: resolve the function by name, decompile, walk the cfunc
body to find the `cot_asg` (for path 8) or `cot_call` (for path 9)
expression, construct a synthetic `ctree_item_t` wrapping it, then call
the `extract_*` function.

**Note:** Paths 8-9 test `extract_*` (the pure matching logic), not
`rename_*` (which calls `hx_view.rename_lvar` — needs a live pseudocode
view that is expensive to construct headlessly). If time permits, a
follow-up can mock `hx_view.rename_lvar` to verify the rename call args.

#### Group 3 — Swap-if engine (paths 10-12)

| # | Function | What it tests | Assertion contract |
|---|---|---|---|
| 10 | `t_swap_inverse_if` | `inverse_if(cif)` on the `if` in `swap_if_else` | After the call: `cif.expr.op == idaapi.cot_lnot`, and the `cif.ithen` / `cif.ielse` branches are swapped (compare their `.ea` before/after). |
| 11 | `t_swap_persistence` | `invert(func_ea, if_ea)` + `get_inverted(func_ea)` | After `invert`: `get_inverted(func_ea)` returns `{if_ea - imagebase}`. After a second `invert` (toggle off): the set is empty. |
| 12 | `t_swap_spaghetti` | `SpaghettiVisitor.apply_to()` on `spaghetti_pattern` | Before the visitor: `cif.ithen.cblock.size() == 2` (the two `x = ...` assignments) and the outer block's last statement is `cit_return`. After the visitor: `cif.ithen.cblock.size() == 3` (the return was appended per `swap_if.py:191`), and the outer block's last statement is also `cit_return` (re-added by `swap_if.py:185-189` because the spilled assignments don't end in return/goto). Assert both: (a) `cif.ithen.cblock.size()` increased by 1, and (b) `str(cfunc)` before ≠ `str(cfunc)` after. This avoids the trap of asserting "return is no longer last" — `swap_if.py:185-189` explicitly re-adds it. |

Setup: resolve `swap_if_else` / `spaghetti_pattern` by name, decompile,
walk the cfunc body to find the `cit_if` citem.

#### Group 4 — Negative offsets (paths 13-15)

| # | Function | What it tests | Assertion contract |
|---|---|---|---|
| 13 | `t_negoffset_detect` | `AnalyseVisitor` on `negative_offset_access` with candidates seeded | After `apply_to`, `store` dict has ≥ 1 entry (the `struct Inner*` lvar). |
| 14 | `t_negoffset_magic_comment` | `_parse_magic_comment` on a synthetic lvar with ` ```Outer+8``` ` comment | Returns a `NegativeLocalInfo` whose `.parent_tinfo.dstr()` endswith `"Outer"` (IDA may prefix with `"struct "` depending on how the type was imported — see `rename.py:187` which strips this prefix) and whose `.offset == 8`. |
| 15 | `t_negoffset_replace` | `ReplaceVisitor` on a cfunc whose lvars have magic comments | After `apply_to`, `str(cfunc)` contains the string `"CONTAINING_RECORD"`. |

Setup for 13: resolve `negative_offset_access`, decompile, find the
`struct Inner*` lvar, add its index to the `candidates` dict, run
`AnalyseVisitor`.

Setup for 14: construct a synthetic `lvar_t` (or mock one) with a
`.cmt` containing ` ```Outer+8``` ` and a `.type()` returning a pointer
to `Inner`. Requires importing `Outer` and `Inner` types into the IDB
first so `tinfo_t.get_named_type(idati, "Outer")` (called inside
`_parse_magic_comment` at `negative_offsets.py:54`) can resolve them.
Use `idaapi.idc_parse_types("struct Inner { int a; int b; }; struct Outer { int header; char pad[4]; struct Inner inner; };", 0)`
— this persists the types into the IDB's Local Types, distinct from
`verify_parity.py`'s existing `_parse()` helper which only produces an
in-memory `tinfo_t` without IDB persistence.

Setup for 15: same as 13, but first call `_set_magic_comment` (a helper
we add to the script) to tag the lvar with the comment, then run
`ReplaceVisitor`.

### Execution Protocol

```bash
# 1. Build test binary (idempotent — skip if .exe is newer than .c)
D:/ProgramFiles/MingW64/bin/gcc.exe -O0 -g \
    -o verification/test_patterns.exe verification/test_patterns.c

# 2. Build plugin archive
python tools/build_plugin.py

# 3. Install into IDA user dir (needed so 'from hexrays_pytools...' imports resolve)
hcli plugin install dist/hexrays_pytools_ng-1.0.0.zip

# 4. Run parity test (GUI mode — scanner paths need PySide6/StructureModel)
"/c/Program Files/IDA Professional 9.4/ida.exe" -A -c \
    -S"verification/verify_parity.py" \
    -L"verification/logs/parity.log" \
    "verification/test_patterns.exe"

# 5. Read results
cat verification/logs/parity_results.json
```

`verify_parity.py` resolves the target by **symbol name**, not index,
so function reordering between rebuilds does not break the test. The
IDA database (`test_patterns.exe.i64`) is created on first run and
reused; delete it to force a fresh auto-analysis.

### Assertion Strategy

Three principles, to avoid the brittleness that killed earlier
attempts at ctree assertions:

1. **Count over content.** Assert `len(model.items) >= 2` rather than
   "model.items[1].name == 'field_b'". Hex-Rays may rename or reorder;
   counts are stable.
2. **Offset sets over name lists.** Assert `{0, 4}.issubset({m.offset
   for m in model.items})` — offsets come from the struct layout, which
   is deterministic from the C source. **Exception:** rename tests
   (paths 8-9) assert on names, because the entire *purpose* of a rename
   test is to verify the name produced. This is acceptable because the
   rename engine's output name comes from the C source lvar name
   (`a2`, `meaningful`), which is itself deterministic at `-O0`.
3. **Structural over textual.** For swap-if, assert `cif.expr.op ==
   cot_lnot` (structural) rather than `"!" in str(cfunc)` (textual).
   For spaghetti, assert "the `return` is no longer the last statement
   of the outer block" (structural) rather than matching a regex on the
   decompiled text.

When an assertion fails, the `detail` field in the JSON output must
contain the actual value (not just "assert False"), so the failure can
be triaged from the JSON without re-running IDA.

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `idat.exe` cannot run PySide6 paths (scanner uses `StructureModel`) | Known | Scanner tests (6-7) run under `ida.exe` (GUI mode). Rename/swap-if/negoffset tests (8-15) use no Qt and could run under `idat.exe`, but we standardize on `ida.exe` for all to keep one command. |
| GCC 8.1.0 produces different Hex-Rays output than MSVC | Low at `-O0` | Patterns are simple (single struct, basic arithmetic). Hex-Rays output at `-O0` is source-like regardless of compiler. If divergence appears, assertions degrade gracefully (count-based, not name-based). |
| `init_hexrays_plugin()` not called in batch mode | Low | `verify_parity.py` already calls it explicitly at top; exploration script confirmed it returns `True` in `idat.exe -A`. |
| IDA auto-analysis renames `scan_simple` to `sub_140001234` | Medium | GCC emits symbol names in the symbol table; `-g` preserves them. Test resolves by `idc.get_name_ea` first, falls back to scanning all functions for a matching size/signature if the name is not found. |
| Scanner paths need `Session.consts` populated | Known | Script constructs a `Session()`, calls `.open()` (populates `consts`), and passes `consts=session.consts` into visitor constructors. |
| Test binary not deterministic across machines | Low | `test_patterns.c` is committed; `.exe` is gitignored and rebuilt by a documented command. The `.i64` is also gitignored. |
| Magic-comment path (14-15) requires `Outer`/`Inner` types in IDB | Known | Script imports the types via `idaapi.idc_parse_types(declaration, 0)` to persist them into Local Types (distinct from `_parse()` which only builds an in-memory tinfo). `_parse_magic_comment` calls `get_named_type(idati, name)` which needs the IDB-persisted form. |

## Testing the Tests

The parity test itself needs a sanity check. After implementation:

1. **Positive case:** Run `verify_parity.py` on `test_patterns.exe`.
   Expect 15/15 PASS (5 existing + 10 new).
2. **Negative case (mutation):** Temporarily break one v2 module (e.g.,
   revert the `_C_KEYWORDS` fix in `member.py`), re-run, confirm the
   relevant parity test FAILS. This proves the test is not vacuously
   passing. Restore the fix, re-run, confirm PASS.
3. **Logger case:** Set `log_level=DEBUG` via HCLI, reload plugin,
   perform one scan, confirm `[HexRaysPyTools][DEBUG]` lines appear in
   the IDA Output window.

## Success Criteria

- [ ] `pytest -v` still passes 532+ tests (with the new
  `test_logging_setup.py` adding ~6 tests → ~538 total).
- [ ] Coverage stays ≥ 80% (logging fix adds coverage, no other change).
- [ ] `mypy --strict` clean (logging_setup.py rewrite is fully typed).
- [ ] `ruff check` clean.
- [ ] `verify_parity.py` reports 15/15 PASS on IDA 9.4 with
  `test_patterns.exe`.
- [ ] Setting `log_level=DEBUG` via HCLI produces visible
  `[HexRaysPyTools][DEBUG]` trace in IDA Output window.
- [ ] Mutation check: reverting `9f8060b` causes `t_get_udt_member` to
  FAIL (proves the test is not vacuous).
