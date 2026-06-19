# Changelog

## [2.0.0] - 2026-06-18

### Major rewrite
- Modern packaging: HCLI `ida-plugin.json` manifest, source distribution ZIP
- 5-layer architecture: pure / infra / domain / plugin entry / ui
- `Session` dataclass replaces all global mutable state
- `ActionRegistry` with explicit 27-action list (no side-effect imports)
- `HxCallbackManager` for explicit hxe_* callback handling
- `py.typed`-friendly type hints throughout; `mypy --strict` clean
- Pytest with 80%+ coverage gate
- PySide6 only (PyQt5 dropped)

### Bug fixes (14 known bugs from original)

| # | Bug | Resolution |
|---|-----|------------|
| B1 | `FormToPyQtWidget` crashes under PySide6 | `FormToPySideWidget` everywhere |
| B2 | `QRegExp.indexIn` removed in Qt6 | `re.search` (stdlib) |
| B3 | `setFilterRegExp` deprecated → renamed in Qt6 | `setFilterRegularExpression` |
| B4 | `QRegExp` / Qt5 APIs in classes.py | `re.search` |
| B5 | `logger.warn` deprecated (Py3.7+) | `logger.warning` |
| B6 | `visited_downward/upward` was `list` (O(n²)) | `set` (O(1)) |
| B7 | `idaapi.remove_pointer` deprecated | `tinfo.remove_ptr_or_array()` |
| B8 | `vdui.refresh_ctext()` removed | `vdui.refresh_view(True)` |
| B9 | `format` missing `{}` placeholder in recasts.py:149 | Fixed in toml_template.py: `_to_field_type` helper |
| B10 | Ctrl+N hotkey conflict | `RenameMemberFromFunctionName` → `Ctrl+Alt+N` |
| B11 | Module-level globals (cache, classes, etc.) | `Session` + DI |
| B12 | `idc.create_array` legacy storage | Netnode + auto-migrate |
| B13 | Python 2 compat (`class Foo(object)`, verbose `super()`) | Removed (Python 3.11+ only) |
| B14 | Bare `print()` debugging | `logger.debug()` |

### Feature parity
- All 27 user-facing actions preserved
- All 4 Hex-Rays event handlers (MemberDoubleClick, PotentialNegativeCollector, StructXrefCollector, SilentIfSwapper) preserved
- Hotkey assignments preserved (with B10 fix)
- IDA 9.0–9.2 supported

### Architecture changes
- `VirtualTable` collision resolved: `DiscoveredVTable` (working copy, in `domain/recon/`) vs `RegisteredVTable` (Local Types view, in `domain/browser/`)
- `core/classes.py` (618 LOC god module) split into 4 focused browser files
- `core/temporary_structure.py` (1073 LOC) split into `domain/recon/{member,discovered_vtable,structure_model,workspace}.py`
- `core/helper.py` (435 LOC god module) split into `domain/types/{tinfo_utils,func_type,udt_builder}.py` + `domain/ctree/ctree_utils.py` + `infra/{idb/netnode,arch/arch}.py`
