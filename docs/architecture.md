# HexRaysPyTools Architecture

## 5-layer model

```
Layer 1: pure/     — Pure Python, no IDA dependency (pytest-friendly)
Layer 2: infra/    — Thin IDA wrappers (mockable)
Layer 3: domain/   — Business logic (IDA-coupled, mostly Qt-free)
Layer 4: plugin/   — Entry point: init/run/term + Session
Layer 5: ui/       — Qt widgets (PySide6, IDA-coupled)
```

Strict downward-only dependencies.

## Module map

- `pure/`: `name_mangle`, `scoring`, `toml_template`, `result` (no IDA)
- `infra/`: `arch`, `idb/netnode` (thin IDA wrappers)
- `domain/types/`: `tinfo_utils`, `func_type`, `udt_builder`
- `domain/scanner/`: `visitor_base`, `scanned_object`, `ctree_utils`, `member_extractor`
- `domain/recon/`: `member`, `discovered_vtable`, `structure_model`, `workspace`
- `domain/xrefs/`: `xref_storage` (netnode-backed with auto-migrate)
- `domain/templated/`: `templated_types` (wraps pure/toml_template)
- `domain/til/`: `type_library` (no ctypes FFI)
- `domain/graph/`: `structure_graph` (set-based DFS)
- `domain/ctree/`: `recast`, `rename`, `swap_if`, `negative_offsets`
- `domain/browser/`: `registered_class`, `registered_vtable`, `tree_model`, `proxy_model`
- `domain/actions/`: base classes + 27 action classes + 4 event handlers
- `ui/`: `chooser`, `widgets/{structure_builder,class_viewer,graph_viewer}`

## Session lifecycle

`MyPlugin.init()` → `Session.open()` → `ActionRegistry.register_all()` → `HxCallbackManager.install()` → register 4 event handlers
`MyPlugin.term()` → `HxCallbackManager.detach_all()` → `ActionRegistry.unregister_all()` → `Session.close()`
