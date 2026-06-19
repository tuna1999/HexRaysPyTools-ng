# Phase A.9 Brief: Port MemberDoubleClick event handler

**Date:** 2026-06-19
**Phase:** A.9 of port-menu-actions research
**Goal:** Wire the `hxe_double_click` event handler to navigate from a
struct member double-click to the virtual function at that member's
address.

## Source

`refs/.../callbacks/member_double_click.py` (43 LOC).

## What's ported

### `choose_virtual_func_address` helper

Two signatures (from the original — the call site picks which):
1. `choose_virtual_func_address(name)` — find EA by name only (for struct
   refs without vtable info)
2. `choose_virtual_func_address(name, class_tinfo, vtable_offset)` — find
   the address of the vtable entry that overrides the method at the
   given offset

Uses `session.demangled_names` (already on `Session` — Phase A.1
foundation) to look up the EA.

### `MemberDoubleClick.handle(event, *args)` in `hx_events.py`

Reads the clicked item:
- `cot_memptr` / `cot_memref` — struct member access
- Two cases:
  1. **Direct member** (`item.e.x.op == cot_memref`) — navigate to the
     function at that member's address (imported/known symbol).
  2. **Vtable method** (`item.e.x.op == cot_memptr` + parent reference)
     — resolve through the vtable to the implementing function.

Wires the session in (`session.demangled_names`).

## Tests

The handler reads `item.e.x.type.get_pointed_object()` etc — pure mockable
helpers but the action itself needs a real `hx_view.item` shape. Tests
cover:
- `choose_virtual_func_address(name)` returns the right EA when name is
  in the demangled_names cache.
- `choose_virtual_func_address(name)` returns None when no match.
- `MemberDoubleClick.handle` is constructible + stores session.

## Quality gates

- `pytest tests/domain/actions/` — pass
- `mypy --strict` — clean
- `ruff check` — clean
- Full `pytest` — 80%+ coverage (omit hx_events.py for ctree + handler-coupled paths)

## Files

```
src/hexrays_pytools/infra/arch/arch.py                   (+choose_virtual_func_address)
src/hexrays_pytools/domain/actions/hx_events.py          (port MemberDoubleClick)
pyproject.toml                                           (+hx_events.py to omit)
tests/domain/actions/test_hx_events.py                   (+3-4 tests)
```