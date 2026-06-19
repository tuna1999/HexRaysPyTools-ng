# Phase 3 coverage fix: report

## Status: DONE_WITH_CONCERNS

The brief's scoped change (graph_viewer test expansion) is complete, correct,
and committed. All 8 tests pass; `graph_viewer.py` went from 34% → 100%.
However, the brief's premise — that this single change would push the global
coverage gate to 80% — does not hold. Total coverage reached **76.76%**, still
3.24 pp short of the 80% gate.

## Commit

- SHA: `1cc589d4c39a226d5dc5beadb8ad99dca535e1cd`
- Subject: `test(ui): add coverage for graph_viewer methods (boost Phase 3 to gate)`
- Files changed: `tests/ui/widgets/test_graph_viewer.py` (+81/-2)

## What was done

Replaced the 1-test smoke file with the brief's 8-test version covering
`OnGetText` (name / no-name fallback), `OnHint` (tooltip / no-tooltip),
`OnDblClick` (change_selected path / no-method guard), and `OnRefresh`
(node + edge build). graph_viewer method coverage is now complete.

## Deviations from the brief

Two intentional deviations, both required to make the brief's tests actually
pass and stay clean:

1. **Test 5 assertion corrected.** The brief asserted `"Foo" in call_args[0][0]`,
   checking that the *string* is in the set passed to `change_selected`. The
   production code at `graph_viewer.py:42` calls
   `self._graph.change_selected({node})` — it passes the **node object** (a
   `MagicMock`), not its name string. The brief's assertion would always fail
   (string hash ≠ MagicMock hash). Changed to `assert node in passed_set`,
   which correctly verifies the set membership of the actual node. The test's
   intent (verify `change_selected` is called with a set containing the node)
   is preserved and the test now passes.

2. **Import formatting + `# type: ignore` annotations.** ruff (`I001`) required
   a blank line after `import os` to match the sibling `test_class_viewer.py`
   convention (side-effect env var set on the next line). Added
   `# type: ignore[assignment]` on the `gv.__class__.__getitem__ = lambda ...`
   monkeypatches so the file stays mypy-clean alongside the project's
   `--strict` config. `from unittest.mock import MagicMock` was added per the
   brief's instruction.

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/ui/widgets/test_graph_viewer.py -v` | 8 passed |
| `ruff check` (source + test) | All checks passed |
| `mypy --strict src/.../graph_viewer.py` | Success: no issues found |
| Full suite `pytest` | 153 passed |
| Global coverage | **76.76%** (gate 80% — NOT met) |

### Coverage delta

| Metric | Baseline (b5ab84a) | After (1cc589d) |
|--------|-------------------|-----------------|
| `graph_viewer.py` | 34% (21/32 missing) | **100%** (0/32) |
| Total | 74.71% (259/1024 missing) | **76.76%** (238/1024 missing) |
| Tests | 146 | 153 |

graph_viewer contributed +21 covered statements; total moved +2.05 pp.

## Why the gate is still red

To reach 80% the suite needs ≤ 205 missing statements; it currently has 238.
That is ~33 more statements to cover. graph_viewer was the only "pure method"
file the brief identified; the remaining gap lives in modules whose uncovered
lines are genuinely harder or out of Phase-3 widget scope.

Largest remaining gaps (missing statements):

| File | Stmts | Missing | % |
|------|------:|--------:|---:|
| `plugin.py` | 30 | 30 | 0% |
| `tree_model.py` | 103 | 57 | 45% |
| `registered_class.py` | 37 | 17 | 54% |
| `structure_model.py` | 51 | 17 | 67% |
| `structure_builder.py` | 29 | 15 | 48% |
| `class_viewer.py` | 31 | 16 | 48% |
| `type_library.py` | 43 | 12 | 72% |
| `logging_setup.py` | 9 | 3 | 67% |

## Recommended next step (to actually close the gate)

The single highest-value, lowest-risk addition is a focused test for
`plugin.py` (0% → likely ~100%): the `HexRaysPyToolsPlugin` classmethods
(`init`, `run`, `term`) are plain functions that can be exercised by mocking
`idaapi.init_hexrays_plugin` / `Session.open` / `Session.close`. That alone is
~30 statements and would lift total to ~79.6%. Pairing it with
`logging_setup.py` (3 stmts) and a couple of `tree_model.py` /
`registered_class.py` branches would cross 80%.

These are **not** in this commit's scope (the brief scoped this change to
`test_graph_viewer.py` only). Flagging for the Phase-3 gate owner (Task 3.7)
to decide: either expand the gate-fix work to the files above, or lower /
scope the gate.
