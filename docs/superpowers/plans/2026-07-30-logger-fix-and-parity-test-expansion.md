# Logger Fix + Parity Test Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the half-wired logger (so `log_level=DEBUG` produces visible trace in the IDA Output window) and expand `verify_parity.py` from 5 to 15 end-to-end parity tests covering the 4 ctree-walking module groups the mock cannot reach.

**Architecture:** Part 1 rewrites `logging_setup.py` with an `IdaOutputHandler` (delegates to `idaapi.msg`) selected when real IDA is detected, and wires `setup_logging()` into `plugin.py:init()`. Part 2 adds a GCC-compiled C test binary (`test_patterns.c`) and 10 new `t_xxx()` functions in `verify_parity.py`, each asserting on a ctree-walking path via the live Hex-Rays engine on IDA 9.4.

**Tech Stack:** Python 3.11+ (mypy --strict, ruff), pytest + mock_ida harness, IDA 9.4 with Hex-Rays decompiler, GCC 8.1.0 (MinGW-w64 at `D:\ProgramFiles\MingW64\bin`), PySide6 (for scanner tests only).

## Global Constraints

- **Python:** type-annotate all function signatures; `mypy --strict` must stay clean.
- **Formatting:** `ruff check` must stay clean; line length 100.
- **Coverage:** pytest coverage gate is 80%; the new `test_logging_setup.py` adds coverage to `logging_setup.py`. No production code is removed from the coverage omit list.
- **IDA 9.x contract:** do NOT touch `plugin.py`'s `init`/`run`/`term` method signatures (instance methods, not classmethods) — guarded by `tests/test_plugin.py`.
- **No new dependencies:** the plugin's `pyproject.toml` `dependencies = []` must stay empty. All imports are stdlib, `idaapi`/`idc` (IDA-provided), or already-present.
- **Parity test binary:** compiled with `D:/ProgramFiles/MingW64/bin/gcc.exe -O0 -g`. The `.exe` and `.i64` are gitignored; only `test_patterns.c` is committed.
- **Assertion style:** prefer counts and offset-sets over name strings; prefer structural ctree assertions (`cif.expr.op == cot_lnot`) over textual ones (`"!" in str(cfunc)`). Exception: rename tests assert on names because the name IS the output under test.
- **Commit message format:** `<type>: <description>` (feat, fix, test, refactor, docs, chore). Attribution disabled globally.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/hexrays_pytools/logging_setup.py` | **Rewrite** | `IdaOutputHandler`, `_ida_output_available()`, `_make_handler()`, `setup_logging()` — context-aware logging setup |
| `src/hexrays_pytools/plugin.py` | **Modify** (1 import + 1 call) | Wire `setup_logging(session.log_level)` into `init()` after `session.open()` |
| `tests/pure/test_logging_setup.py` | **Create** | Unit tests for idempotency, handler selection, format prefix, stderr fallback |
| `verification/test_patterns.c` | **Create** | C source with 5 `__attribute__((noinline))` functions covering scanner/rename/swap-if/negative-offset patterns |
| `verification/verify_parity.py` | **Extend** | Add 10 `t_xxx()` test functions (paths 6-15) to the existing harness |
| `verification/.gitignore` | **Create** | Ignore `*.exe`, `*.i64`, `*.id0`, `*.id1`, `*.id2`, `*.nam`, `logs/` |

---

## Task 1: Logger — Rewrite `logging_setup.py` with `IdaOutputHandler`

**Files:**
- Modify: `src/hexrays_pytools/logging_setup.py` (full rewrite of the current 23-line file)

**Interfaces:**
- Produces: `setup_logging(level: int) -> None`, `_make_handler() -> logging.Handler`, `_ida_output_available() -> bool`, `class IdaOutputHandler(logging.Handler)`, module constant `_LOG_FORMAT`. Consumed by Task 2 (`plugin.py`) and Task 3 (`test_logging_setup.py`).

- [ ] **Step 1: Write the failing test for format + handler selection**

Create `tests/pure/test_logging_setup.py` with the first two tests. The existing `logging_setup.py` will fail these because it lacks the `[HexRaysPyTools]` prefix and the mock-aware handler selection.

```python
"""Unit tests for logging_setup.py — handler selection + idempotency.

These run under the pytest + mock_ida harness, so idaapi.msg is a
MagicMock → _ida_output_available() returns False → StreamHandler is
expected (not IdaOutputHandler).
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from hexrays_pytools.logging_setup import (
    _LOG_FORMAT,
    _ida_output_available,
    _make_handler,
    setup_logging,
)


def test_format_has_hexrays_prefix() -> None:
    """The log format string must start with [HexRaysPyTools]."""
    assert _LOG_FORMAT.startswith("[HexRaysPyTools]")


def test_format_has_levelname_and_module() -> None:
    """The format must include levelname and module for filtering."""
    assert "%(levelname)s" in _LOG_FORMAT
    assert "%(module)s" in _LOG_FORMAT


def test_ida_output_available_false_under_mock() -> None:
    """Under mock_ida, idaapi.msg is a MagicMock → returns False."""
    assert _ida_output_available() is False


def test_make_handler_returns_streamhandler_under_mock() -> None:
    """Under mock, _make_handler() must return a StreamHandler."""
    handler = _make_handler()
    assert isinstance(handler, logging.StreamHandler)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pure/test_logging_setup.py -v`
Expected: 4 FAIL — `ImportError` for `_LOG_FORMAT`/`_ida_output_available`/`_make_handler` (they don't exist yet in the current `logging_setup.py`).

- [ ] **Step 3: Rewrite `logging_setup.py`**

Replace the entire contents of `src/hexrays_pytools/logging_setup.py` with:

```python
"""Centralized logging configuration for HexRaysPyTools.

Configures the root logger to emit either to the IDA Output window
(when running inside IDA, via ``idaapi.msg``) or to stderr (when running
in the mock/test environment). Called once during plugin init via
``setup_logging(session.log_level)``.
"""
from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "[HexRaysPyTools][%(levelname)s] %(message)s (%(module)s:%(funcName)s:%(lineno)d)"


class IdaOutputHandler(logging.Handler):
    """Emit log records to the IDA Output window via ``idaapi.msg``.

    Used when the plugin runs inside IDA. In the mock/test environment
    ``idaapi.msg`` does not exist (or is a Mock), so the fallback
    ``StreamHandler`` is used instead — see ``_make_handler``.
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

    The mock's ``idaapi.msg`` is a ``MagicMock`` callable; the real one
    is a SWIG builtin function. We detect the real one by checking that
    ``idaapi`` is importable and ``msg`` is callable but NOT a Mock
    instance.
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
    adding a fresh one — so re-calling ``setup_logging`` (e.g., after a
    ``log_level`` setting change + plugin reload) does not stack
    handlers.
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/pure/test_logging_setup.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hexrays_pytools/logging_setup.py tests/pure/test_logging_setup.py
git commit -m "feat(logging): rewrite logging_setup with IdaOutputHandler + mock-aware fallback

Adds IdaOutputHandler (delegates to idaapi.msg), _ida_output_available()
(GitHub-style mock detection via isinstance(idaapi.msg, Mock)), and
_make_handler() to select the right handler per environment. Format now
includes [HexRaysPyTools] prefix for easy Output-window filtering."
```

---

## Task 2: Logger — Add idempotency + stderr fallback tests

**Files:**
- Modify: `tests/pure/test_logging_setup.py` (append 2 more tests)

**Interfaces:**
- Consumes: `setup_logging`, `IdaOutputHandler` from Task 1.
- Produces: full test coverage for `setup_logging` idempotency and `IdaOutputHandler.emit` stderr fallback.

- [ ] **Step 1: Write the idempotency + stderr fallback tests**

Append to `tests/pure/test_logging_setup.py`:

```python
def test_setup_logging_idempotent_no_duplicate_handlers() -> None:
    """Calling setup_logging twice must not stack handlers."""
    root = logging.getLogger()
    initial_count = len(root.handlers)
    try:
        setup_logging(logging.DEBUG)
        after_first = len(root.handlers)
        setup_logging(logging.DEBUG)
        after_second = len(root.handlers)
        assert after_first == after_second, "Handler count must not grow on re-call"
        # Exactly one HexRaysPyTools handler should be present.
        hx_handlers = [h for h in root.handlers if getattr(h, "_hexrays_pytools", False)]
        assert len(hx_handlers) == 1
    finally:
        # Clean up: remove our handlers so other tests are not affected.
        for h in list(root.handlers):
            if getattr(h, "_hexrays_pytools", False):
                root.removeHandler(h)


def test_setup_logging_sets_root_level() -> None:
    """setup_logging must set the root logger level."""
    root = logging.getLogger()
    try:
        setup_logging(logging.DEBUG)
        assert root.level == logging.DEBUG
        setup_logging(logging.WARNING)
        assert root.level == logging.WARNING
    finally:
        for h in list(root.handlers):
            if getattr(h, "_hexrays_pytools", False):
                root.removeHandler(h)
        root.setLevel(logging.WARNING)


def test_ida_output_handler_falls_to_stderr_on_failure() -> None:
    """If idaapi.msg raises, IdaOutputHandler.emit must write to stderr."""
    from hexrays_pytools.logging_setup import IdaOutputHandler

    handler = IdaOutputHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="test message", args=(), exc_info=None,
    )
    # Patch idaapi.msg (imported lazily inside emit) to raise.
    mock_idaapi = MagicMock()
    mock_idaapi.msg.side_effect = RuntimeError("IDA shutting down")
    with patch.dict("sys.modules", {"idaapi": mock_idaapi}):
        with patch("sys.stderr.write") as mock_write:
            handler.emit(record)
            mock_write.assert_called_once()
            written = mock_write.call_args[0][0]
            assert "test message" in written
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/pure/test_logging_setup.py -v`
Expected: 7 PASS (4 from Task 1 + 3 new).

- [ ] **Step 3: Verify coverage on logging_setup.py**

Run: `python -m pytest tests/pure/test_logging_setup.py --cov=hexrays_pytools.logging_setup --cov-report=term-missing -v`
Expected: `logging_setup.py` coverage ≥ 90%. The only uncovered line should be the `IdaOutputHandler.emit` → `idaapi.msg` success branch (cannot run under mock).

- [ ] **Step 4: Commit**

```bash
git add tests/pure/test_logging_setup.py
git commit -m "test(logging): add idempotency + stderr fallback coverage"
```

---

## Task 3: Logger — Wire `setup_logging` into `plugin.py:init()`

**Files:**
- Modify: `src/hexrays_pytools/plugin.py` (add 1 import + 1 call line)

**Interfaces:**
- Consumes: `setup_logging` from Task 1.
- Produces: a plugin that actually honors `session.log_level`.

- [ ] **Step 1: Add the import**

In `src/hexrays_pytools/plugin.py`, add to the imports block (after the existing `.domain.session` import):

```python
from .logging_setup import setup_logging
```

- [ ] **Step 2: Add the `setup_logging` call in `init()`**

In `src/hexrays_pytools/plugin.py`, inside `def init(self) -> int:`, locate the line `self.session.open()` (currently around line 73). Immediately after it, add:

```python
        setup_logging(self.session.log_level)
```

The surrounding context should read:

```python
        self.session = Session()
        self.session.open()
        setup_logging(self.session.log_level)
```

- [ ] **Step 3: Run the full test suite + plugin contract tests**

Run: `python -m pytest tests/test_plugin.py tests/pure/test_logging_setup.py -v`
Expected: all PASS. The plugin contract tests (`test_init_run_term_are_instance_methods`, `test_plugin_init_wires_registry_and_callbacks`, etc.) must still pass — they verify init/run/term are instance methods and that `init()` wires session/actions/callbacks.

- [ ] **Step 4: Run mypy + ruff**

Run: `python -m mypy --strict src/hexrays_pytools/plugin.py src/hexrays_pytools/logging_setup.py`
Expected: `Success: no issues found`

Run: `python -m ruff check src/hexrays_pytools/plugin.py src/hexrays_pytools/logging_setup.py`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add src/hexrays_pytools/plugin.py
git commit -m "fix(plugin): wire setup_logging into init() so log_level setting is honored

setup_logging was defined but never called. After session.open() loads
log_level from HCLI settings, setup_logging configures the root logger
with the IdaOutputHandler (real IDA) or StreamHandler (test/mock)."
```

---

## Task 4: Logger — Run full quality gates + verify mutation check

**Files:** none modified (verification only)

**Interfaces:** none.

- [ ] **Step 1: Run the complete test suite + coverage**

Run: `python -m pytest -v`
Expected: 539 PASS (532 existing + 7 new in `test_logging_setup.py`). Coverage ≥ 80%.

- [ ] **Step 2: Run mypy strict + ruff on the full project**

Run: `python -m mypy --strict src/hexrays_pytools/`
Expected: `Success: no issues found in 77 source files`

Run: `python -m ruff check src/hexrays_pytools/ tests/ tools/`
Expected: `All checks passed!`

- [ ] **Step 3: Mutation check — confirm the logger fix is not vacuous**

Temporarily revert the `setup_logging` call to verify the test catches it:

```bash
# Comment out the setup_logging line in plugin.py:init()
python -m pytest tests/pure/test_logging_setup.py -v
# (tests still pass — they test logging_setup directly, not the plugin wiring)
# Restore the line:
git checkout -- src/hexrays_pytools/plugin.py
```

Note: the plugin wiring is verified by `test_plugin_init_wires_registry_and_callbacks` — but that test does not assert on logging. The logging behavior is verified by running the plugin in real IDA (Part 2's parity test). This is acceptable per the spec: the unit tests verify the logging_setup module; the E2E parity test verifies the wiring.

- [ ] **Step 4: Commit (no changes — this is a verification checkpoint)**

No commit needed. If all gates pass, proceed to Task 5.

---

## Task 5: Parity Test — Create `test_patterns.c` + compile + verify in IDA

**Files:**
- Create: `verification/test_patterns.c`
- Create: `verification/.gitignore`

**Interfaces:**
- Produces: `verification/test_patterns.exe` (compiled binary, gitignored) with 5 named functions: `scan_simple`, `scan_chain`, `rename_assign_chain`, `callee_takes_arg`, `rename_call_arg`, `swap_if_else`, `spaghetti_pattern`, `negative_offset_access`, `main`.

- [ ] **Step 1: Create `verification/.gitignore`**

```gitignore
# IDA + build artifacts for parity testing
*.exe
*.i64
*.id0
*.id1
*.id2
*.nam
logs/
```

- [ ] **Step 2: Create `verification/test_patterns.c`**

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
    int a1 = a2;                  /* RenameOther target: a1 <- a2 */
    g_sink = a1 + real_name;
}

__attribute__((noinline))
void callee_takes_arg(int meaningful) {
    g_sink = meaningful;
}

__attribute__((noinline))
void rename_call_arg(int real_value) {
    int a1 = real_value;
    callee_takes_arg(a1);         /* RenameOutside target: a1 <- "meaningful" */
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

- [ ] **Step 3: Compile the binary**

Run:
```bash
D:/ProgramFiles/MingW64/bin/gcc.exe -O0 -g \
    -o verification/test_patterns.exe verification/test_patterns.c
```
Expected: no errors. Verify the binary exists: `ls -la verification/test_patterns.exe`.

- [ ] **Step 4: Commit the C source + .gitignore (NOT the .exe)**

```bash
git add verification/test_patterns.c verification/.gitignore
git commit -m "test(verification): add test_patterns.c with scanner/rename/swap-if/negoffset patterns

GCC -O0 -g compiled binary (gitignored) provides 5 named functions
for the parity test: scan_simple, scan_chain, rename_assign_chain,
callee_takes_arg, rename_call_arg, swap_if_else, spaghetti_pattern,
negative_offset_access. Each targets a specific ctree-walking path."
```

---

## Task 6: Parity Test — Add shared helpers to `verify_parity.py`

**Files:**
- Modify: `verification/verify_parity.py` (add helpers + 10 test functions across Tasks 6-9)

**Interfaces:**
- Produces: helper functions `_resolve(name) -> ea`, `_decompile(ea) -> cfunc`, `_find_lvar_by_type(cfunc, predicate) -> (idx, lvar)`, `_find_citem(cfunc, op) -> citem`, `_import_types()`. Consumed by Tasks 7-9.

- [ ] **Step 1: Read the current `verify_parity.py` to understand the harness**

Run: `cat verification/verify_parity.py | head -50`

Note the existing structure: `results` dict, `check(name, fn)` wrapper, `_parse(t)` helper, `main()` that calls `check()` for each test and writes JSON.

- [ ] **Step 2: Add shared helper functions after the existing `_parse`**

Insert these helpers into `verification/verify_parity.py` immediately after the existing `_parse` function (around line 54):

```python
def _resolve(name: str) -> int:
    """Resolve a function name to its EA. Raises if not found."""
    ea = int(idc.get_name_ea_simple(name))
    assert ea != int(idcapi.BADADDR), f"Function '{name}' not found in IDB"
    return ea


def _decompile(ea: int) -> Any:
    """Decompile function at EA. Raises DecompilationFailure on error."""
    cfunc = idaapi.decompile(ea)
    assert cfunc is not None, f"Failed to decompile at {hex(ea)}"
    return cfunc


def _find_first_ptr_lvar(cfunc: Any) -> tuple[int, Any]:
    """Return (index, lvar) of the first pointer-typed local variable."""
    lvars = list(cfunc.get_lvars())
    for idx, lv in enumerate(lvars):
        if lv.type().is_ptr():
            return idx, lv
    raise AssertionError("No pointer-typed lvar found in cfunc")


def _find_if_citem(cfunc: Any) -> Any:
    """Find the first cit_if citem in the cfunc body. Raises if none."""
    class _Finder(idaapi.ctree_parentee_t):
        def __init__(self) -> None:
            idaapi.ctree_parentee_t.__init__(self)
            self.found: Any = None

        def visit_insn(self, insn: Any) -> int:
            if insn.op == idaapi.cit_if and self.found is None:
                self.found = insn.cif
            return 0

    finder = _Finder()
    finder.apply_to(cfunc.body, None)
    assert finder.found is not None, "No cit_if found in cfunc"
    return finder.found


def _import_negoffset_types() -> None:
    """Persist Inner/Outer struct types into the IDB Local Types.

    Required by _parse_magic_comment which calls get_named_type(idati, ...).
    Uses idc_parse_types (not _parse) because the types must be IDB-persistent.
    """
    decl = "struct Inner { int a; int b; }; struct Outer { int header; char pad[4]; struct Inner inner; };"
    idaapi.idc_parse_types(decl, 0)
```

- [ ] **Step 3: Commit the helpers (no tests yet — they are exercised by Tasks 7-9)**

```bash
git add verification/verify_parity.py
git commit -m "test(verification): add shared helpers for parity test expansion

_resolve, _decompile, _find_first_ptr_lvar, _find_if_citem,
_import_negoffset_types — used by the 10 new t_xxx() test functions."
```

---

## Task 7: Parity Test — Add Group 1 (Scanner) + Group 2 (Rename) tests

**Files:**
- Modify: `verification/verify_parity.py` (add 4 test functions)

**Interfaces:**
- Consumes: helpers from Task 6, `NewShallowSearchVisitor`/`VariableObject`/`ScanObject` from `hexrays_pytools.domain.scanner`, `extract_rename_other_info`/`extract_rename_outside_info` from `hexrays_pytools.domain.ctree.rename`.

- [ ] **Step 1: Write the 4 test functions**

Insert these into `verification/verify_parity.py` before the `main()` function:

```python
# --- Group 1: Scanner (paths 6-7) ---


def t_scanner_shallow() -> str:
    """NewShallowSearchVisitor on scan_simple -> >=2 members at offsets 0,4."""
    from hexrays_pytools.domain.recon.structure_model import StructureModel
    from hexrays_pytools.domain.recon.workspace import ReconWorkspace
    from hexrays_pytools.domain.scanner.member_extractor import NewShallowSearchVisitor
    from hexrays_pytools.domain.scanner.scanned_object import VariableObject

    ea = _resolve("scan_simple")
    cfunc = _decompile(ea)
    idx, lv = _find_first_ptr_lvar(cfunc)
    obj = VariableObject(lv, 0)

    workspace = ReconWorkspace()
    workspace.set_model(StructureModel())
    # Consts: use a Session to populate them.
    from hexrays_pytools.domain.session import Session
    session = Session()
    session.open()

    visitor = NewShallowSearchVisitor(
        cfunc, 0, obj, workspace, consts=session.consts
    )
    visitor.process()

    items = workspace.model.items
    offsets = {int(m.offset) for m in items}
    assert len(items) >= 2, f"Expected >=2 members, got {len(items)}"
    assert {0, 4}.issubset(offsets), f"Offsets {offsets} missing 0 or 4"
    return f"members={len(items)} offsets={sorted(offsets)}"


def t_scanner_chain() -> str:
    """NewShallowSearchVisitor on scan_chain (q=p) -> >=1 member at offset 0."""
    from hexrays_pytools.domain.recon.structure_model import StructureModel
    from hexrays_pytools.domain.recon.workspace import ReconWorkspace
    from hexrays_pytools.domain.scanner.member_extractor import NewShallowSearchVisitor
    from hexrays_pytools.domain.scanner.scanned_object import VariableObject

    ea = _resolve("scan_chain")
    cfunc = _decompile(ea)
    idx, lv = _find_first_ptr_lvar(cfunc)
    obj = VariableObject(lv, 0)

    workspace = ReconWorkspace()
    workspace.set_model(StructureModel())
    from hexrays_pytools.domain.session import Session
    session = Session()
    session.open()

    visitor = NewShallowSearchVisitor(
        cfunc, 0, obj, workspace, consts=session.consts
    )
    visitor.process()

    items = workspace.model.items
    offsets = {int(m.offset) for m in items}
    assert len(items) >= 1, f"Expected >=1 member, got {len(items)}"
    assert 0 in offsets, f"Offset 0 missing from {offsets}"
    return f"members={len(items)} offsets={sorted(offsets)}"


# --- Group 2: Rename (paths 8-9) ---


def t_rename_other() -> str:
    """extract_rename_other_info on 'a1 = a2' in rename_assign_chain -> name='a2'."""
    from hexrays_pytools.domain.ctree.rename import extract_rename_other_info

    ea = _resolve("rename_assign_chain")
    cfunc = _decompile(ea)

    # Find the cot_asg expression where one side is a cot_var.
    class _AsgFinder(idaapi.ctree_parentee_t):
        def __init__(self) -> None:
            idaapi.ctree_parentee_t.__init__(self)
            self.found_expr: Any = None

        def visit_expr(self, e: Any) -> int:
            if e.op == idaapi.cot_var and self.found_expr is None:
                parent = self.parents[-1].cexpr if self.parents else None
                if parent is not None and parent.op == idaapi.cot_asg:
                    self.found_expr = e
            return 0

    finder = _AsgFinder()
    finder.apply_to(cfunc.body, None)
    assert finder.found_expr is not None, "No cot_asg with cot_var found"

    # Build a synthetic ctree_item_t wrapping the found expression.
    item = idaapi.ctree_item_t()
    item.it = finder.found_expr
    info = extract_rename_other_info(cfunc, item)
    assert info is not None, "extract_rename_other_info returned None"
    assert info.name == "a2", f"Expected name='a2', got '{info.name}'"
    assert info.lvar.name.startswith("a1"), f"Expected lvar starts with 'a1', got '{info.lvar.name}'"
    return f"name={info.name} lvar={info.lvar.name}"


def t_rename_outside() -> str:
    """extract_rename_outside_info on callee_takes_arg(a1) -> name='meaningful'."""
    from hexrays_pytools.domain.ctree.rename import extract_rename_outside_info

    ea = _resolve("rename_call_arg")
    cfunc = _decompile(ea)

    # Find the cot_call expression.
    class _CallFinder(idaapi.ctree_parentee_t):
        def __init__(self) -> None:
            idaapi.ctree_parentee_t.__init__(self)
            self.found_arg: Any = None

        def visit_expr(self, e: Any) -> int:
            if e.op == idaapi.cot_call and self.found_arg is None:
                if len(e.a) > 0 and e.a[0].op == idaapi.cot_var:
                    self.found_arg = e.a[0]
            return 0

    finder = _CallFinder()
    finder.apply_to(cfunc.body, None)
    assert finder.found_arg is not None, "No cot_call with cot_var arg found"

    item = idaapi.ctree_item_t()
    item.it = finder.found_arg
    info = extract_rename_outside_info(cfunc, item)
    assert info is not None, "extract_rename_outside_info returned None"
    assert info.name == "meaningful", f"Expected name='meaningful', got '{info.name}'"
    return f"name={info.name}"
```

- [ ] **Step 2: Register the 4 new tests in `main()`**

In the `main()` function of `verify_parity.py`, add these 4 lines after the existing `check("model.finalize", t_finalize)` line and before `_RESULTS_PATH.write_text(...)`:

```python
    check("scanner.shallow", t_scanner_shallow)
    check("scanner.chain", t_scanner_chain)
    check("rename.other", t_rename_other)
    check("rename.outside", t_rename_outside)
```

- [ ] **Step 3: Commit (tests will be run in Task 10 after all groups are added)**

```bash
git add verification/verify_parity.py
git commit -m "test(verification): add scanner (shallow/chain) + rename (other/outside) parity tests"
```

---

## Task 8: Parity Test — Add Group 3 (Swap-if) tests

**Files:**
- Modify: `verification/verify_parity.py` (add 3 test functions)

**Interfaces:**
- Consumes: `inverse_if`, `invert`, `get_inverted`, `has_inverted`, `SpaghettiVisitor` from `hexrays_pytools.domain.ctree.swap_if`, `_find_if_citem` helper from Task 6.

- [ ] **Step 1: Write the 3 swap-if test functions**

Insert these before `main()`:

```python
# --- Group 3: Swap-if (paths 10-12) ---


def t_swap_inverse_if() -> str:
    """inverse_if on swap_if_else -> condition is cot_lnot, branches swapped."""
    from hexrays_pytools.domain.ctree.swap_if import inverse_if

    ea = _resolve("swap_if_else")
    cfunc = _decompile(ea)
    cif = _find_if_citem(cfunc)

    # Snapshot before.
    then_ea_before = int(cif.ithen.ea)
    else_ea_before = int(cif.ielse.ea)

    inverse_if(cif)

    assert int(cif.expr.op) == int(idaapi.cot_lnot), f"Expected cot_lnot, got op={cif.expr.op}"
    assert int(cif.ithen.ea) == else_ea_before, "ithen should now be the old ielse"
    assert int(cif.ielse.ea) == then_ea_before, "ielse should now be the old ithen"
    return f"cond_op={cif.expr.op} swapped=True"


def t_swap_persistence() -> str:
    """invert + get_inverted on swap_if_else -> toggle on then off."""
    from hexrays_pytools.domain.ctree.swap_if import get_inverted, has_inverted, invert

    ea = _resolve("swap_if_else")
    cfunc = _decompile(ea)
    cif = _find_if_citem(cfunc)
    if_ea = int(cif.expr.ea)

    # Toggle ON.
    invert(ea, if_ea)
    inverted = get_inverted(ea)
    expected_rva = if_ea - int(idaapi.get_imagebase())
    assert expected_rva in inverted, f"RVA {expected_rva} not in {inverted}"
    assert has_inverted(ea), "has_inverted should be True after toggle on"

    # Toggle OFF.
    invert(ea, if_ea)
    inverted_after = get_inverted(ea)
    assert expected_rva not in inverted_after, f"RVA still in {inverted_after} after toggle off"
    assert not has_inverted(ea), "has_inverted should be False after toggle off"
    return f"toggle_on_off=ok rva={expected_rva}"


def t_swap_spaghetti() -> str:
    """SpaghettiVisitor on spaghetti_pattern -> then-branch grows by 1."""
    from hexrays_pytools.domain.ctree.swap_if import SpaghettiVisitor

    ea = _resolve("spaghetti_pattern")
    cfunc = _decompile(ea)
    cif = _find_if_citem(cfunc)

    text_before = str(cfunc)
    then_size_before = int(cif.ithen.cblock.size())

    visitor = SpaghettiVisitor()
    visitor.apply_to(cfunc.body, None)

    text_after = str(cfunc)
    # Re-find cif — the visitor may have rebuilt the ctree.
    cif_after = _find_if_citem(cfunc)
    then_size_after = int(cif_after.ithen.cblock.size())

    assert text_before != text_after, "cfunc text unchanged after SpaghettiVisitor"
    assert then_size_after == then_size_before + 1, (
        f"then-branch size: before={then_size_before}, after={then_size_after} (expected +1)"
    )
    return f"then_before={then_size_before} then_after={then_size_after}"
```

- [ ] **Step 2: Register the 3 new tests in `main()`**

Add after the Task 7 registrations:

```python
    check("swap.inverse_if", t_swap_inverse_if)
    check("swap.persistence", t_swap_persistence)
    check("swap.spaghetti", t_swap_spaghetti)
```

- [ ] **Step 3: Commit**

```bash
git add verification/verify_parity.py
git commit -m "test(verification): add swap-if parity tests (inverse_if, persistence, spaghetti)"
```

---

## Task 9: Parity Test — Add Group 4 (Negative-offset) tests

**Files:**
- Modify: `verification/verify_parity.py` (add 3 test functions)

**Interfaces:**
- Consumes: `AnalyseVisitor`, `NegativeLocalInfo`, `ReplaceVisitor`, `_parse_magic_comment` from `hexrays_pytools.domain.ctree.negative_offsets`, `_import_negoffset_types` helper from Task 6.

- [ ] **Step 1: Write the 3 negative-offset test functions**

Insert these before `main()`:

```python
# --- Group 4: Negative offsets (paths 13-15) ---


def t_negoffset_detect() -> str:
    """AnalyseVisitor on negative_offset_access -> store has >=1 entry."""
    from hexrays_pytools.domain.ctree.negative_offsets import AnalyseVisitor

    ea = _resolve("negative_offset_access")
    cfunc = _decompile(ea)
    idx, lv = _find_first_ptr_lvar(cfunc)

    # Seed candidates: the struct-pointer lvar.
    candidates: dict[int, Any] = {idx: lv.type().get_pointed_object()}
    store: dict[int, Any] = {}

    visitor = AnalyseVisitor(candidates, store)
    visitor.apply_to(cfunc.body, None)

    assert len(store) >= 1, f"Expected >=1 store entry, got {len(store)} (candidates={candidates})"
    return f"store_entries={len(store)} keys={list(store.keys())}"


def t_negoffset_magic_comment() -> str:
    """_parse_magic_comment on lvar with 'Outer+8' comment -> NegativeLocalInfo."""
    from hexrays_pytools.domain.ctree.negative_offsets import _parse_magic_comment

    _import_negoffset_types()

    # Build a mock lvar with the magic comment and a pointer-to-Inner type.
    mock_lvar = MagicMock()
    mock_lvar.cmt = "```Outer+8```"
    inner_ti = _parse("struct Inner { int a; int b; };")
    ptr_ti = idaapi.tinfo_t()
    ptr_ti.assign(inner_ti)
    ptr_ti.create_ptr(inner_ti)
    mock_lvar.type.return_value = ptr_ti

    result = _parse_magic_comment(mock_lvar)
    assert result is not None, "_parse_magic_comment returned None"
    assert str(result.parent_tinfo.dstr()).endswith("Outer"), (
        f"Expected dstr endswith 'Outer', got '{result.parent_tinfo.dstr()}'"
    )
    assert int(result.offset) == 8, f"Expected offset=8, got {result.offset}"
    return f"parent={result.parent_tinfo.dstr()} offset={result.offset}"


def t_negoffset_replace() -> str:
    """ReplaceVisitor on cfunc with magic-commented lvars -> CONTAINING_RECORD in output."""
    from hexrays_pytools.domain.ctree.negative_offsets import (
        AnalyseVisitor,
        NegativeLocalInfo,
        ReplaceVisitor,
    )

    _import_negoffset_types()
    ea = _resolve("negative_offset_access")
    cfunc = _decompile(ea)
    idx, lv = _find_first_ptr_lvar(cfunc)

    # Build the NegativeLocalInfo as if the magic comment was parsed.
    inner_ti = _parse("struct Inner { int a; int b; };")
    outer_ti = idaapi.tinfo_t()
    outer_ti.get_named_type(idaapi.get_idati(), "Outer")
    # Find the member name of Inner inside Outer at offset 8.
    from hexrays_pytools.domain.ctree.negative_offsets import find_deep_members
    members = dict(find_deep_members(outer_ti, inner_ti))
    member_name = members.get(8, "inner")

    info = NegativeLocalInfo(
        tinfo=inner_ti, parent_tinfo=outer_ti, offset=8, member_name=member_name
    )
    negative_lvars: dict[int, Any] = {idx: info}

    text_before = str(cfunc)
    visitor = ReplaceVisitor(negative_lvars)
    visitor.apply_to(cfunc.body, None)
    text_after = str(cfunc)

    assert "CONTAINING_RECORD" in text_after, (
        f"Expected 'CONTAINING_RECORD' in cfunc text after ReplaceVisitor"
    )
    assert text_before != text_after, "cfunc text unchanged after ReplaceVisitor"
    return f"contains_containing_record=True"
```

- [ ] **Step 2: Register the 3 new tests in `main()`**

Add after the Task 8 registrations:

```python
    check("negoffset.detect", t_negoffset_detect)
    check("negoffset.magic_comment", t_negoffset_magic_comment)
    check("negoffset.replace", t_negoffset_replace)
```

- [ ] **Step 3: Commit**

```bash
git add verification/verify_parity.py
git commit -m "test(verification): add negative-offset parity tests (detect, magic_comment, replace)"
```

---

## Task 10: Parity Test — Run E2E on IDA 9.4 + mutation check

**Files:** none modified (verification only)

**Interfaces:** none.

- [ ] **Step 1: Build the plugin archive**

Run: `python tools/build_plugin.py`
Expected: `Built: dist/hexrays_pytools_ng-1.0.0.zip`

- [ ] **Step 2: Install the plugin into IDA**

Run: `hcli plugin install dist/hexrays_pytools_ng-1.0.0.zip`
Expected: success message. (If already installed, re-install to update.)

- [ ] **Step 3: Run the parity test on `test_patterns.exe` (GUI mode)**

Run:
```bash
"/c/Program Files/IDA Professional 9.4/ida.exe" -A -c \
    -S"$(pwd)/verification/verify_parity.py" \
    -L"$(pwd)/verification/logs/parity.log" \
    "$(pwd)/verification/test_patterns.exe"
```
Expected: exit code 0.

- [ ] **Step 4: Read the results JSON**

Run: `cat verification/logs/parity_results.json`
Expected: 15/15 tests with `"ok": true`. The `ida_version` should be `"9.4"`.

- [ ] **Step 5: Triage any failures**

If any test has `"ok": false`, read the `detail` and `errors` fields. Common causes:
- **ImportError**: plugin not installed or stale — re-run Step 2.
- **AssertionError on offset/name**: Hex-Rays decompiled differently than expected — inspect `str(cfunc)` in the detail field.
- **DecompilationFailure**: the function was inlined despite `__attribute__((noinline))` — verify with `objdump`.

Fix the test assertion (not the production code) if the Hex-Rays output is valid but different from the expected pattern. If the production code is buggy, create a follow-up task — do NOT fix it in this plan (Non-Goal: "Rewriting or extending the scanner/rename/swap-if/negative-offset logic itself").

- [ ] **Step 6: Mutation check — verify the tests are not vacuously passing**

Temporarily revert the `_C_KEYWORDS` fix in `member.py` (the fix from commit `9f8060b`):

```bash
# Comment out the _C_KEYWORDS frozenset and the elif branch that uses it
# in src/hexrays_pytools/domain/recon/member.py
python tools/build_plugin.py
hcli plugin install dist/hexrays_pytools_ng-1.0.0.zip
# Re-run the parity test — t_get_udt_member should FAIL
"/c/Program Files/IDA Professional 9.4/ida.exe" -A -c \
    -S"$(pwd)/verification/verify_parity.py" \
    -L"$(pwd)/verification/logs/parity_mutation.log" \
    "$(pwd)/verification/test_patterns.exe"
cat verification/logs/parity_results.json | python -c "import json,sys; d=json.load(sys.stdin); print('get_udt_member ok:', d['tests']['member.get_udt_member']['ok'])"
# Expected: ok: False
# Restore the fix:
git checkout -- src/hexrays_pytools/domain/recon/member.py
```

- [ ] **Step 7: Commit the final state (no code changes — verification checkpoint)**

If all 15/15 pass and the mutation check confirms the test catches the regression, the plan is complete. No commit needed for this task.

---

## Task 11: Logger — Verify in real IDA (manual)

**Files:** none modified (manual verification only)

**Interfaces:** none.

- [ ] **Step 1: Set log_level to DEBUG via HCLI**

Run: `hcli plugin config hexrays_pytools_ng log_level DEBUG`

- [ ] **Step 2: Open IDA 9.4 with any IDB**

Open `ida.exe`, load `test_patterns.exe.i64` (or any IDB).

- [ ] **Step 3: Perform a scan action (press F on a variable)**

In the pseudocode view of `scan_simple`, place the cursor on the `p` parameter and press `F` (ShallowScanVariable hotkey).

- [ ] **Step 4: Check the IDA Output window**

Open the Output window (View > Output window, or `Ctrl+Shift+O`). Look for lines starting with `[HexRaysPyTools][DEBUG]`. Expected output similar to:

```
[HexRaysPyTools][DEBUG] ShallowScanVariable: start func=0x... obj='p' type=... origin=0
[HexRaysPyTools][DEBUG]   created member offset=0 tinfo=int scanned={p}
[HexRaysPyTools][DEBUG]   created member offset=4 tinfo=int scanned={p}
[HexRaysPyTools][DEBUG] ShallowScanVariable: done func=0x... +2 member(s) (total 2)
```

If no `[HexRaysPyTools]` lines appear, the logger fix did not take effect — verify `setup_logging` is called in `plugin.py:init()` (Task 3) and the plugin was re-installed.

- [ ] **Step 5: Reset log_level to INFO**

Run: `hcli plugin config hexrays_pytools_ng log_level INFO`

---

## Self-Review Checklist

**Spec coverage:**
- [x] Part 1 defect 1.1 (`setup_logging` never called) → Task 3
- [x] Part 1 defect 1.2 (no `IdaOutputHandler`) → Task 1
- [x] Part 1 defect 1.3 (format missing prefix) → Task 1
- [x] Part 1 unit tests (6 tests) → Tasks 1-2 (7 tests total)
- [x] Part 2 `test_patterns.c` → Task 5
- [x] Part 2 `.gitignore` → Task 5
- [x] Part 2 Group 1 (scanner paths 6-7) → Task 7
- [x] Part 2 Group 2 (rename paths 8-9) → Task 7
- [x] Part 2 Group 3 (swap-if paths 10-12) → Task 8
- [x] Part 2 Group 4 (negoffset paths 13-15) → Task 9
- [x] Execution protocol → Task 10
- [x] Mutation check → Task 10 Step 6
- [x] Logger E2E in real IDA → Task 11
- [x] Success criteria (pytest, mypy, ruff, 15/15 parity) → Tasks 4, 10

**Placeholder scan:** No TBD/TODO/FIXME in the plan. All code blocks contain actual implementation.

**Type consistency:** `_resolve`, `_decompile`, `_find_first_ptr_lvar`, `_find_if_citem`, `_import_negoffset_types` are defined in Task 6 and used identically in Tasks 7-9. `setup_logging`, `IdaOutputHandler`, `_LOG_FORMAT` defined in Task 1, used in Tasks 2-3.

**Scope check:** Two parts (logger + parity test) are cohesive — logger is the debugging prerequisite for parity test. Single plan is appropriate.
