# Phase A.11 Brief: Port form-request actions (ShowGraph/Classes/StructureBuilder)

**Date:** 2026-06-19
**Phase:** A.11 of port-menu-actions research
**Goal:** Wire the 3 actions that open Qt widgets to the actual
``StructureGraphViewer`` / ``ClassViewer`` / ``StructureBuilder`` widgets.

## Source

`refs/.../callbacks/form_requests.py` (85 LOC).

## What's ported

### `ShowGraph`

* Widget type: BWN_LOCTYPS (Local Types chooser)
* Action: build a :class:`StructureGraph` from
  ``ctx.chooser_selection``, wrap in ``StructureGraphViewer``, show
* Idempotent — re-shows the existing graph if one is open

### `ShowClasses`

* Widget type: BWN_PSEUDOCODE
* Action: open or activate a ``ClassViewer`` (built from
  ``ProxyModel`` + ``TreeModel``)
* Idempotent — activates the existing viewer if one is open

### `ShowStructureBuilder`

* Menu: right-click in pseudocode
* Action: open or activate ``StructureBuilder`` (built from the session's
  workspace model)
* Idempotent — activates the existing builder if one is open

All 3 actions are excluded from the coverage gate (Qt + IDA widgets
require a real GUI).

## Tests

- `test_show_graph_action_constructible`
- `test_show_classes_action_constructible`
- `test_show_structure_builder_action_constructible`
- `test_show_structure_builder_check_returns_true`

## Quality gates

- `pytest tests/domain/actions/` — pass
- `mypy --strict` — clean
- `ruff check` — clean
- Full `pytest` — 80%+ coverage (omit `form_requests.py`)

## Files

```
src/hexrays_pytools/domain/actions/form_requests.py     (port 3 actions)
pyproject.toml                                          (+form_requests.py to omit)
tests/domain/actions/test_form_requests.py              (+4 tests)
```