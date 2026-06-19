# Phase A.12 Brief: Finish CreateVtable import

**Date:** 2026-06-19
**Phase:** A.12 of port-menu-actions research (last phase)
**Goal:** Wire `CreateVtable.activate()` to actually create a vtable
struct in IDA's Local Types and persist it.

## Source

`refs/.../callbacks/virtual_table_creation.py` (35 LOC) +
`refs/.../core/temporary_structure.py:VirtualTable.import_to_structures`
(382-410).

## What's ported

### `DiscoveredVTable.import_to_structures(ask=False)`

Reads N function pointers starting from ``self.offset`` (or the address
passed at construction time), builds a UDT with one ``void*`` member per
pointer, and registers it via :func:`type_library.create_type`.

Naming convention: ``vtable_<hex_offset>``.

The `ask=True` flag shows the generated declaration in IDA's ask-text
dialog for user confirmation.

### `CreateVtable.activate()`

Replaces the stub with a real call to
``DiscoveredVTable(offset=0, tinfo=None, name=..., origin=0).import_to_structures()``.

## Tests

- `test_discovered_vtable_import_to_structures_creates_type` —
  patched `type_library.create_type`, verify call args
- `test_create_vtable_action_activates_without_crash`

## Quality gates

- `pytest tests/` — pass
- `mypy --strict` — clean
- `ruff check` — clean
- Full `pytest` — 80%+ coverage

## Files

```
src/hexrays_pytools/domain/recon/discovered_vtable.py    (+import_to_structures)
src/hexrays_pytools/domain/actions/struct_creation.py   (port CreateVtable)
tests/domain/recon/test_discovered_vtable.py            (+2 tests)
```