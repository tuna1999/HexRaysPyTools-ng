# Task 2.15 Report: Phase 2 gate verification

**Status: BLOCKED** — mypy gate fails on one stale `type: ignore`. Tag was NOT created.

## Verification Commands

### 1. Full test suite (with coverage gate) — PASS

```
PYTHONPATH=src python -m pytest -v
```

Result: **120 passed in 0.50s**

Coverage gate (`--cov-fail-under=80`): **passed at 82.36%**

Key Phase 2 test coverage (per-module):

| Module | Stmts | Miss | Cover |
|---|---|---|---|
| domain/graph/structure_graph.py | 103 | 17 | 83% |
| domain/recon/discovered_vtable.py | 21 | 0 | 100% |
| domain/recon/member.py | 41 | 5 | 88% |
| domain/recon/structure_model.py | 51 | 17 | 67% |
| domain/recon/workspace.py | 17 | 1 | 94% |
| domain/scanner/ctree_utils.py | 6 | 0 | 100% |
| domain/scanner/member_extractor.py | 17 | 0 | 100% |
| domain/scanner/scanned_object.py | 24 | 6 | 75% |
| domain/scanner/visitor_base.py | 19 | 0 | 100% |
| domain/templated/templated_types.py | 39 | 2 | 95% |
| domain/til/type_library.py | 43 | 12 | 72% |
| domain/types/func_type.py | 24 | 5 | 79% |
| domain/types/tinfo_utils.py | 19 | 3 | 84% |
| domain/types/udt_builder.py | 11 | 0 | 100% |
| domain/xrefs/xref_storage.py | 58 | 13 | 78% |

TOTAL: 737 stmts, 130 missed, **82%** overall.

### 2. Type check (mypy --strict) — FAIL

```
PYTHONPATH=src python -m mypy --strict src/hexrays_pytools/
```

Output:

```
src\hexrays_pytools\domain\session.py:17: error: Unused "type: ignore" comment  [unused-ignore]
Found 1 error in 1 file (checked 42 source files)
```

Root cause: `session.py:17` carries `# type: ignore[import-untyped]` on the
`from .templated.templated_types import TemplatedTypes` line. `TemplatedTypes`
is now fully typed (imports from the well-typed `pure.toml_template`), so the
ignore became stale. One-line fix: delete the comment. Not applied — brief
forbids modifying files.

### 3. Lint (ruff) — PASS

```
python -m ruff check src/hexrays_pytools/ tests/ tools/
```

Output:

```
All checks passed!
```

### 4. Phase 2 deliverables — ALL PRESENT

```
domain/types/      __init__.py  tinfo_utils.py  func_type.py  udt_builder.py
domain/scanner/    __init__.py  visitor_base.py  scanned_object.py  ctree_utils.py  member_extractor.py
domain/recon/      __init__.py  workspace.py  member.py  discovered_vtable.py  structure_model.py
domain/xrefs/      __init__.py  xref_storage.py
domain/templated/  __init__.py  templated_types.py  data/__init__.py  data/templated_types.toml
domain/til/        __init__.py  type_library.py
domain/graph/      __init__.py  structure_graph.py
```

## Deliverable checklist

### domain/types/
- [x] `__init__.py`
- [x] `tinfo_utils.py`
- [x] `func_type.py`
- [x] `udt_builder.py`

### domain/scanner/
- [x] `__init__.py`
- [x] `visitor_base.py`
- [x] `scanned_object.py`
- [x] `ctree_utils.py`
- [x] `member_extractor.py`

### domain/recon/
- [x] `__init__.py`
- [x] `workspace.py` (updated in refactor commit 75ad42c)
- [x] `member.py`
- [x] `discovered_vtable.py`
- [x] `structure_model.py`

### domain/xrefs/
- [x] `__init__.py`
- [x] `xref_storage.py`

### domain/templated/
- [x] `__init__.py`
- [x] `templated_types.py`
- [x] `data/__init__.py`
- [x] `data/templated_types.toml`

### domain/til/
- [x] `__init__.py`
- [x] `type_library.py`

### domain/graph/
- [x] `__init__.py`
- [x] `structure_graph.py`

**Deliverables: 27/27 present (24+ required).**

## Tag

**NOT created.** `git tag phase-2-core-domain` was not run because the mypy
gate failed. Per brief: "If all gates pass, tag." They did not all pass.

## Gate summary

| Gate | Result |
|---|---|
| pytest (120 tests, 80% coverage gate) | PASS — 120 passed, 82.36% |
| mypy --strict | **FAIL** — 1 unused `type: ignore` in `session.py:17` |
| ruff check | PASS |
| Deliverables present | PASS — 27/27 |

## Remediation (one-line fix, not applied per brief)

Remove `# type: ignore[import-untyped]` from
`src/hexrays_pytools/domain/session.py:17`. After that, re-run mypy; if clean,
rerun this gate and create the tag.

## Final coverage

**82.36%** (gate threshold: 80%).

## Status

**BLOCKED** — mypy gate fails on one stale `type: ignore`. All other gates
pass and all 27 deliverables exist. Apply the one-line fix and rerun to
unblock the `phase-2-core-domain` tag.
