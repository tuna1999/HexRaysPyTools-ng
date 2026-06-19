# Phase A.10 Brief: Port StructXrefCollector event handler

**Date:** 2026-06-19
**Phase:** A.10 of port-menu-actions research
**Goal:** Wire the `hxe_maturity / CMAT_FINAL` event handler to populate
`XrefStorage` with struct-field cross-references from every function.

## Source

`refs/.../callbacks/struct_xref_collector.py` (107 LOC).

## What's ported

### `StructXrefCollectorVisitor(idaapi.ctree_parentee_t)`

Walks the cfunc body looking for ``cot_memptr`` / ``cot_memref``
expressions. For each match:
- Reads the struct type's ordinal (via :func:`get_ordinal`)
- Records the field offset, EA (closest ancestor's EA), and access
  type (R / W / Arg)
- Aggregates by ``{ordinal: {field_offset: [(offset, line, type), ...]}}``
- On `process()`: hands the dict to `XrefStorage` for persistence

The visit logic itself is excluded from the coverage gate (live ctree
walk), but the dict construction + XrefStorage integration is testable.

### `StructXrefCollector.handle(event, *args)` in `hx_events.py`

At ``CMAT_FINAL``, builds the visitor and runs `process()`. Passes the
session's `XrefStorage` (not a fresh one) so the data persists across
events.

## XrefStorage API mismatch

The original ``XrefStorage.update(func_offset, result_dict)`` accepts the
whole ``{ordinal: {field_offset: [...]}}`` shape in one call. Our new
XrefStorage API is per-(ordinal, field_offset):

```python
def update(self, func_offset: int, ordinal: int, field_xrefs: list[tuple[Any, ...]]) -> None:
```

→ The visitor calls `update(func_offset, ordinal, [xref_info])` once per
field_offset (matches the new API granularity). Storage shape stays
`_storage[ordinal][func_offset] = field_xrefs`.

## Tests

- `test_struct_xref_collector_handle_does_not_raise`
- `test_struct_xref_collector_handle_at_cmat_final_stores_data`
  (verifies the visitor processes a cfunc and XrefStorage gets populated)
- `test_struct_xref_collector_uses_session_storage` (verifies the
  handler uses `session.xrefs`, not a fresh XrefStorage)

## Quality gates

- `pytest tests/domain/actions/` — pass
- `mypy --strict` — clean
- `ruff check` — clean
- Full `pytest` — 80%+ coverage (omit hx_events.py)

## Files

```
src/hexrays_pytools/domain/actions/hx_events.py          (port StructXrefCollector)
tests/domain/actions/test_hx_events.py                   (+2 tests)
```