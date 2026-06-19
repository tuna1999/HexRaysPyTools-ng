# Task 4.2 Report: domain/actions/registry.py

## Status: DONE

## Commit
- **SHA:** `e18918d`
- **Subject:** `feat(actions): add ActionRegistry (explicit 27-action list, no side effects)`

## Files (2)
| Path | Purpose |
|------|---------|
| `src/hexrays_pytools/domain/actions/registry.py` | `ActionRegistry` + `ACTION_CLASSES` (27-entry explicit tuple) |
| `tests/domain/actions/test_registry.py` | 6 unit tests |

## TDD Summary
- **RED:** Wrote `test_registry.py` first; ran pytest -> `ModuleNotFoundError: No module named 'hexrays_pytools.domain.actions.registry'` (collection error, 0 tests). Confirmed tests fail before implementation exists.
- **GREEN:** Wrote `registry.py` per the brief (verbatim source). All 6 tests pass.
- **REFACTOR:** No behavior change. Applied mechanical fixes required by the brief's "mypy/ruff clean" gate (see Deviations).

## Tests (6/6)
| Test | Purpose |
|------|---------|
| `test_action_classes_count` | `ACTION_CLASSES` has 27 entries |
| `test_registry_init_empty` | Fresh registry exposes empty `actions` list |
| `test_registry_with_session` | Constructor injects session (`_session is session`) |
| `test_registry_build_actions_returns_27` | `_build_actions` returns 27 instances (monkey-patched; real lazy import deferred to Task 4.5) |
| `test_registry_register_one_appends` | `_register_one` appends to `actions` |
| `test_registry_unregister_all_clears` | `unregister_all` clears `_actions` |

## Verification Gates
| Gate | Result |
|------|--------|
| `pytest tests/domain/actions/test_registry.py` | 6/6 passed |
| `mypy --strict src/hexrays_pytools/domain/actions/registry.py` | Success: no issues found |
| `ruff check registry.py test_registry.py` | All checks passed |
| Full suite regression | 190 passed (was 184 after Task 4.1; +6 new) |
| Project coverage | 82.32% (gate: ≥80%) |

## Notes / Deviations

The brief's "verbatim" source did not satisfy the `mypy --strict` / `ruff check` gates as-is. Same situation as Task 4.1. Mechanical fixes only; no functional deviation.

### 1. ruff `I001` (import sorting) + `F401` (unused import)

`ruff --fix` reordered:
- The lazy-import block inside `_build_actions`: ruff sorts imports alphabetically by module name (`containing_structure` -> `form_requests` -> `function_signature` -> `guess_allocation` -> ...) and expands multi-name `from X import a, b, c` lines to one-per-line. This changes only the *order of import statements*; the runtime class list `all_classes` below remains in spec order (Form requests -> Function signature -> Scanners -> ... -> Containing structure), which is what determines actual registration order.
- Removed unused `import pytest` from `test_registry.py` (F401).

### 2. Forward-reference mypy `[import-untyped]` (11 lazy imports)

The referenced action modules (`form_requests`, `function_signature`, `scanners`, `struct_xref`, `struct_creation`, `structs_by_size`, `guess_allocation`, `swap_if_action`, `recast_action`, `rename_action`, `containing_structure`) are explicitly not yet created (Task 4.5). Under `mypy --strict`, mypy reported `[import-untyped]` for each because the parent `hexrays_pytools` package is importable, so mypy treats the missing submodules as installed-but-untyped rather than missing.

Added per-import `# type: ignore[import-untyped]` comments. This follows the exact precedent set by Task 1.3 (`session.py`), Task 1.7, and Task 2.11 for the same forward-reference pattern. These ignores become removable once the referenced modules ship with a `py.typed` marker in Task 4.5.

Added a comment block above the imports explaining this.

### 3. mypy `[type-arg]` on module-level generics

Added `# type: ignore[type-arg]` to:
- `ACTION_CLASSES: tuple = (...)` (module-level constant)
- `self._actions: list = []` (`__init__` attribute)

This matches the brief's existing `# type: ignore[type-arg]` on the `_build_actions`, `_register_one`, and `actions` method return annotations. Consistent style across the file.

## Coverage Note

`registry.py` standalone coverage is 57% — uncovered lines are the body of `_build_actions` (lazy imports + class list, lines 77-129), `register_all` (69-70), and the popup branch of `_register_one` (142). This is by design: the real `_build_actions` is intentionally untested here because the action modules do not exist yet; test #4 monkey-patches it to return 27 mocks. The overall project coverage (82.32%) clears the 80% gate. Full coverage of `_build_actions` lands with Task 4.5 once the 27 action classes exist.

## Notes for Downstream Tasks

- **Task 4.5 (action files):** Once the 11 action modules are created with a `py.typed` marker, remove the 11 `# type: ignore[import-untyped]` comments (lines 77-111) and the explanatory comment block (74-76). Under `warn_unused_ignores = true`, leaving them will fail mypy.
- **Task 4.5:** Add integration coverage for `register_all` / `_build_actions` (real path, not mocked) to lift `registry.py` standalone coverage.
- The `all_classes` list inside `_build_actions` is the source of truth for registration order; the `ACTION_CLASSES` tuple is the documentation/spec mirror.
