# Task 1.7 Report: Phase 1 gate verification

**Date:** 2026-06-18
**Working dir:** D:\re_dev_projects\ida-plugins\HexRaysPyTools
**Status:** DONE_WITH_CONCERNS

## Summary

Phase 1 infrastructure is functionally complete: all 58 tests pass, coverage
exceeds the 80% gate, ruff is clean, the plugin entry point imports under
`mock_ida`, the Session roundtrip works, and all 13 deliverables exist.

However, the `mypy --strict` gate (verification command 2) FAILS with 2
`unused-ignore` errors in `src/hexrays_pytools/domain/session.py`. Per the
brief, the `phase-1-infrastructure` tag may only be created if **all** gates
pass. Because mypy did not pass, the tag was NOT created.

This task is verification-only (no file modifications permitted), so the mypy
errors were reported, not fixed.

## Verification command outputs

### Command 1: Full test suite

```
$ PYTHONPATH=src python -m pytest -v
... (58 tests) ...
tests/pure/test_toml_template.py::test_render_unknown_template_returns_err PASSED [100%]

=============================== tests coverage ===============================
_______________ coverage: platform win32, python 3.14.5-final-0 _______________

Name                                            Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------------
src\hexrays_pytools\__init__.py                     2      0   100%
src\hexrays_pytools\__main__.py                     2      2     0%   6-8
src\hexrays_pytools\domain\__init__.py              0      0   100%
src\hexrays_pytools\domain\recon\__init__.py        0      0   100%
src\hexrays_pytools\domain\recon\workspace.py      14      0   100%
src\hexrays_pytools\domain\session.py              47      3    94%   62, 73-74
src\hexrays_pytools\domain\settings.py             30      2    93%   57-58
src\hexrays_pytools\infra\__init__.py               0      0   100%
src\hexrays_pytools\infra\arch\__init__.py          0      0   100%
src\hexrays_pytools\infra\arch\arch.py              9      0   100%
src\hexrays_pytools\infra\idb\__init__.py           0      0   100%
src\hexrays_pytools\infra\idb\netnode.py           19      2    89%   38, 42
src\hexrays_pytools\logging_setup.py                9      3    67%   19-21
src\hexrays_pytools\plugin.py                      30     30     0%   7-54
src\hexrays_pytools\pure\__init__.py                1      0   100%
src\hexrays_pytools\pure\name_mangle.py            14      0   100%
src\hexrays_pytools\pure\result.py                 26      0   100%
src\hexrays_pytools\pure\scoring.py                14      0   100%
src\hexrays_pytools\pure\toml_template.py          28      2    93%   86-87
-----------------------------------------------------------------------------
TOTAL                                             245     44    82%
Required test coverage of 80% reached. Total coverage: 82.04%
============================= 58 passed in 0.19s =============================
```

**Result: PASS** — 58/58 tests, 82.04% coverage (>= 80% gate).

### Command 2: Type check — FAIL

```
$ PYTHONPATH=src python -m mypy --strict src/hexrays_pytools/
src\hexrays_pytools\domain\session.py:16: error: Unused "type: ignore" comment  [unused-ignore]
src\hexrays_pytools\domain\session.py:70: error: Unused "type: ignore" comment  [unused-ignore]
Found 2 errors in 1 file (checked 19 source files)
$ echo $?
1
```

**Result: FAIL** (exit 1). Two `unused-ignore` errors.

Root cause: `session.py` annotates imports of sibling in-package modules
(`recon/workspace.py`, `settings.py`) with `# type: ignore[import-untyped]`.
Under `--strict`, mypy treats these as typed (part of the package being
checked), so the `[import-untyped]` ignores are unused.

- Line 16: `from .recon.workspace import ReconWorkspace  # type: ignore[import-untyped]`
- Line 70: `from .settings import load_into  # type: ignore[import-untyped]`

The fix (NOT applied — verification-only task) is to delete the two
`# type: ignore[import-untyped]` comments, or scope them to a different
error code. These modules exist in the package and are typed.

### Command 3: Lint — PASS

```
$ python -m ruff check src/hexrays_pytools/ tests/ tools/
All checks passed!
$ echo $?
0
```

**Result: PASS.**

### Command 4: Plugin entry import — PASS

(mock_ida preinstalled as instructed)

```
$ PYTHONPATH=src python -c "
import sys; sys.path.insert(0, 'tools')
import mock_ida; mock_ida.install()
from hexrays_pytools.__main__ import PLUGIN_ENTRY
print(PLUGIN_ENTRY)
"
<class 'hexrays_pytools.plugin.HexRaysPyToolsPlugin'>
```

**Result: PASS.** `PLUGIN_ENTRY` resolves to the plugin class.

### Command 5: Session roundtrip — PASS

```
$ PYTHONPATH=src python -c "
import sys; sys.path.insert(0, 'tools')
import mock_ida; mock_ida.install()
from hexrays_pytools.domain.session import Session
s = Session()
s.open()
s.imported_ea.add(0x1000)
s.close()
print(f'Session works: cached 0x{0x1000:x}')
"
Session works: cached 0x1000
```

**Result: PASS.** Session open → mutate → close works end to end.

### Command 6: List Phase 1 deliverables

All 13 files present (see checklist below).

## Deliverables checklist (13/13)

| # | Path | Status |
|---|------|--------|
| 1 | `src/hexrays_pytools/infra/__init__.py` (empty) | ✓ |
| 2 | `src/hexrays_pytools/infra/arch/__init__.py` (empty) | ✓ |
| 3 | `src/hexrays_pytools/infra/arch/arch.py` | ✓ (861 B) |
| 4 | `src/hexrays_pytools/infra/idb/__init__.py` (empty) | ✓ |
| 5 | `src/hexrays_pytools/infra/idb/netnode.py` | ✓ (1526 B) |
| 6 | `src/hexrays_pytools/domain/__init__.py` (empty) | ✓ |
| 7 | `src/hexrays_pytools/domain/session.py` | ✓ (3038 B) |
| 8 | `src/hexrays_pytools/domain/settings.py` | ✓ (1774 B) |
| 9 | `src/hexrays_pytools/domain/recon/__init__.py` (empty) | ✓ |
| 10 | `src/hexrays_pytools/domain/recon/workspace.py` | ✓ (1137 B) |
| 11 | `src/hexrays_pytools/plugin.py` | ✓ (1709 B) |
| 12 | `src/hexrays_pytools/__main__.py` | ✓ (290 B) |
| 13 | `tools/hexrays_pytools_entry.py` | ✓ (493 B) |

Plus `tools/mock_ida.py` (updated in Tasks 1.1 and 1.6) — present.

**Result: 13/13 deliverables exist.**

## Gate summary

| Gate | Command | Result |
|------|---------|--------|
| Tests + coverage | `pytest -v` | ✓ PASS — 58/58, 82.04% |
| Type check | `mypy --strict` | ✗ FAIL — 2 unused-ignore errors |
| Lint | `ruff check` | ✓ PASS |
| Plugin import | `PLUGIN_ENTRY` | ✓ PASS |
| Session roundtrip | Session open/close | ✓ PASS |
| Deliverables | 13 files | ✓ PASS — 13/13 |

**5 of 6 verification commands pass. mypy --strict fails.**

## Tag

**NOT created.** The brief states the `phase-1-infrastructure` tag may only be
created if all gates pass. The mypy strict gate (command 2) failed with exit 1,
so the tag was intentionally withheld.

Suggested follow-up (outside this verification task): remove the two
`# type: ignore[import-untyped]` comments at
`src/hexrays_pytools/domain/session.py:16` and `:70`, then re-run command 2
and tag.

## Final coverage

**82.04%** (>= 80% gate; `--cov-fail-under=80` not lowered, as instructed).

## Status

**DONE_WITH_CONCERNS**

- Phase 1 is functionally complete and all behavioral gates pass.
- The mypy `--strict` gate fails on 2 unused `type: ignore` comments (a
  trivial, mechanical fix that is out of scope for this verification-only task).
- The `phase-1-infrastructure` tag was deliberately withheld because not all
  gates passed.
