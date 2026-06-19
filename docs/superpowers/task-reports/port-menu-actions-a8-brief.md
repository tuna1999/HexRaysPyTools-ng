# Phase A.8 Brief: Port PropagateName action

**Date:** 2026-06-19
**Phase:** A.8 of port-menu-actions research
**Goal:** Wire the last rename action to the recursive visitor engine.

## Source

`refs/.../callbacks/renames.py:323-399` (~77 LOC).

## What's ported

### `_is_default_name(name)` helper

Regex match for the IDA-generated default names: `a1`, `v3`, `var_5`,
`field_12`, `qword_8`, etc. If a variable has a default name, propagating
the user's selected name is more useful.

### `_NamePropagator(RecursiveObjectDownwardsVisitor)`

Walks every place a tracked object is referenced (current function + all
callees), renaming:
- **Global variable** — `idaapi.set_name(obj_ea, new_name)` (with `_` prefix
  loop on collision)
- **Local variable** — `hx_view.rename_lvar(lvar, new_name, True)`
- **Struct member** — `change_member_name(struct_name, offset, new_name)`

Uses the `_start_iteration` / `_finish` lifecycle hooks (Phase A.4) to
switch the pseudocode view to each callee's cfunc as it's scanned.

Skips renaming when:
- `self.crippled` is True (the function is a thunk — the type belongs to
  the caller, not the passthrough)
- The current name is NOT a default name AND
  `session.propagate_through_all_names` is False (user opted out)

### `PropagateName(HexRaysPopupAction)`

Hotkey `P`, menu_path `HexRaysPyTools/Rename/`.

- `check(hx_view)`:
  - citype == VDI_EXPR
  - `ScanObject.create(cfunc, ctree_item)` returns non-None
  - `not _is_default_name(obj.name)` (the obj has a real name to propagate)
- `activate(ctx)`:
  - Build the visitor with `(hx_view, cfunc, obj)`
  - `visitor.process()`
  - `hx_view.refresh_view(True)`

## Tests

End-to-end visitor walk is verified in real IDA via idat headless. Tests
cover the pure helpers + the check predicate + the no-crash `activate()`
contract.

### test_rename_action.py (extend existing)
1. `test_is_default_name_matches_a_v_pattern`
2. `test_is_default_name_matches_word_field_off_pattern`
3. `test_is_default_name_rejects_real_names`
4. `test_propagate_name_check_rejects_non_vdi_expr`
5. `test_propagate_name_check_rejects_default_name`
6. `test_propagate_name_check_accepts_real_name`
7. `test_propagate_name_instantiable_and_activates_no_crash`

## Quality gates

- `pytest tests/domain/actions/` — pass
- `mypy --strict` — clean
- `ruff check` — clean
- Full `pytest` — 80%+ coverage (omit `rename_action.py` for ctree-coupled activate)

## Out of scope

- The actual ctree walk — verified in real IDA.

## Files

```
src/hexrays_pytools/domain/actions/rename_action.py     (rewrite PropagateName)
pyproject.toml                                          (+rename_action.py to omit)
tests/domain/actions/test_rename_action.py              (+7 tests)
```
