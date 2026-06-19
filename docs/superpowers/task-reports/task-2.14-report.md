# Task 2.14 Report: domain/graph/structure_graph.py

## Status: DONE

## Commit

- **SHA:** `b0f22f24d315262825e901b3c187cec18c070669`
- **Subject:** `feat(graph): add StructureGraph (set-based DFS, fixes B6 O(n²) bug)`
- **Files changed:** 4 files, 140 insertions

## Files Created

1. `src/hexrays_pytools/domain/graph/__init__.py` (empty)
2. `src/hexrays_pytools/domain/graph/structure_graph.py`
3. `tests/domain/graph/__init__.py` (empty)
4. `tests/domain/graph/test_structure_graph.py`

## TDD Summary

### RED Phase

Wrote `tests/domain/graph/test_structure_graph.py` first (6 tests). Ran pytest — failed at collection:

```
ModuleNotFoundError: No module named 'hexrays_pytools.domain.graph.structure_graph'
```

RED confirmed: 0 tests collected, import error before any test runs.

### GREEN Phase

Implemented `src/hexrays_pytools/domain/graph/structure_graph.py` per the brief verbatim, then ran the suite:

```
6 passed in 0.05s
```

- test_local_type_default_fields PASSED
- test_structure_graph_init_empty PASSED
- test_visited_sets_are_sets PASSED
- test_get_nodes_empty_graph PASSED
- test_get_edges_empty_graph PASSED
- test_change_selected_updates_ordinal_list PASSED

## Quality Gates

| Gate | Result |
|------|--------|
| pytest (6/6) | PASS |
| mypy --strict | PASS — "Success: no issues found in 1 source file" |
| ruff check | PASS — "All checks passed!" |

## Deviations from Brief

The brief's verbatim content triggered 3 ruff lint errors that had to be fixed to satisfy the verification gate. Both fixes preserve behavior:

1. **B007 (source):** `for ordinal, lt in self.local_types.items()` — `lt` was unused. Changed to `for ordinal in self.local_types:` (iterate keys directly).
2. **B007 (source):** `for member in udt:` — `member` was unused. Changed to `for _ in udt:`.
3. **I001 (test):** Import order `StructureGraph, LocalType` was not alphabetical. Reordered to `LocalType, StructureGraph`.

The brief's `# type: ignore[import-not-found]` on `import idaapi` is retained, consistent with the rest of the `domain/` package (e.g. `scanner/visitor_base.py`, `til/type_library.py`).

## Bug Fixes Carried Forward

- **B6 (O(n²) membership):** `visited_downward` / `visited_upward` are now `set[int]` (was `list` in the original `core/structure_graph.py`). `test_visited_sets_are_sets` enforces this.
- **B5 (`logger.warn` deprecation):** Module uses `logging.getLogger(__name__)` only; the legacy `logger.warn` call from the original is gone (no `warn` usage anywhere in the rewrite).
