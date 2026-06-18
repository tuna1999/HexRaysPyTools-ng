# HexRaysPyTools Rewrite — Design Spec

**Date:** 2026-06-18

**Status:** Draft — pending user review

**Target version:** 2.0.0

**Target platform:** IDA Pro 9.0–9.2 (Python 3.11+)

---

## 1. Executive Summary

Rewrite the legacy `HexRaysPyTools` IDA plugin (~6567 LOC, Python 2/3 hybrid, IDA 7.x targeting) into a modern, fully-tested, HCLI-packaged plugin targeting IDA 9.x. Preserve 100% of the 27 user-facing actions and 4 Hex-Rays event handlers. Fix 14 documented bugs in the process. Reorganize the codebase into a 5-layer architecture with explicit dependency injection and zero global mutable state.

**Key outcomes:**

1. Plugin installable via Hex-Rays HCLI (`ida-plugin.json` manifest)
2. 80%+ test coverage enforced by CI
3. 100% feature parity with the original
4. All known critical bugs (Qt6 incompatibility, Py2 dead code, hotkey conflict) fixed
5. Clear module boundaries enabling future contributors to add features safely

---

## 2. Goals &amp; Non-Goals

### 2.1 Goals (in scope)

- **Full feature parity** with the original plugin (27 actions + 4 event handlers)
- **Modern packaging** via HCLI `ida-plugin.json` (source distribution, no PyPI)
- **IDA 9.x native** — drop Python 2 compatibility, use `tomllib`, `match/case`, modern f-strings
- **PySide6 only** — drop PyQt5 fallback, fix `FormToPyQtWidget` bug
- **Type-safe** — full type hints on public API, `mypy --strict` clean
- **Testable** — pytest with IDA API mocks, 80% coverage gate
- **No global mutable state** — `Session` dataclass + dependency injection
- **Bug fixes** — all 14 known bugs addressed (see Section 8)

### 2.2 Non-Goals (out of scope)

- **PyPI distribution** — source-only distribution for v2.0.0; PyPI may be a v2.1+ effort
- **IDA 8.x or earlier** — minimum is IDA 9.0; 8.4 is not supported
- **New features** — this is a rewrite, not a feature addition
- **Plugin UI redesign** — UX is preserved as-is; visual polish deferred
- **Multi-language support** — all user-facing strings remain in English (matching the original)

---

## 3. Architecture

### 3.1 Five-layer dependency model

```
Layer 5: Qt UI (PySide6 widgets, IDA-coupled)
   ↑
Layer 4: Plugin Entry & Wiring (init/run/term, registry)
   ↑
Layer 3: Domain Logic (IDA-coupled, no Qt)
   ↑
Layer 2: Infrastructure (IDA-thin wrappers, arch, storage)
   ↑
Layer 1: Pure Python (no IDA, pytest-friendly)
```

Strict dependency direction: each layer depends only on layers below it.

**Layer 1 — `pure/`:** Pure-Python logic that needs no IDA at all. Easily testable. Examples: `name_mangle.py` (sanitize demangled C++ names), `scoring.py` (member collision scoring heuristic), `toml_template.py` (validate &amp; render templated types TOML), `result.py` (`Result`/`Option` types).

**Layer 2 — `infra/`:** Thin wrappers around IDA API to enable easy mocking. Examples: `ida_api/hexrays.py` (re-export `ida_hexrays.*`), `idb/netnode.py` (netnode storage helpers), `arch/arch.py` (`is_code_ea`, `get_ptr` with ARM/x86 abstraction), `logging.py` (centralized logger).

**Layer 3 — `domain/`:** The business logic of the plugin. No Qt code in this layer except the `QAbstractTableModel` subclass in `domain/recon/structure_model.py`. Sub-packages: `types/`, `scanner/`, `recon/`, `browser/`, `xrefs/`, `graph/`, `templated/`, `til/`, `ctree/`, `actions/`.

**Layer 4 — Plugin entry &amp; wiring:** `plugin.py` (the `plugin_t` subclass), `__main__.py` (defines `PLUGIN_ENTRY`), `session.py` (the state container), `settings.py` (HCLI settings wrapper), `logging_setup.py`.

**Layer 5 — `ui/`:** Qt widgets that depend on domain layer models injected via constructor. Examples: `widgets/structure_builder.py`, `widgets/class_viewer.py`, `widgets/graph_viewer.py`, `chooser.py`.

### 3.2 Session — the state container

The `Session` dataclass replaces all module-level global mutable state from the original (`cache.py`, `variable_scanner.py`, `classes.py`, `temporary_structure.py`).

```python
@dataclass
class Session:
    is_open: bool = False
    idb_path: str = ""
    recon: ReconWorkspace | None = None
    xrefs: XrefStorage | None = None
    templated: TemplatedTypes | None = None
    imported_ea: set[int] = field(default_factory=set)
    demangled_names: dict[str, set[int]] = field(default_factory=dict)
    touched_functions: set[int] = field(default_factory=set)
    log_level: int = logging.INFO
    propagate_through_all_names: bool = False
    store_xrefs: bool = True
    scan_any_type: bool = False
    templated_types_file: str = ""
```

Lifecycle: `MyPlugin.init()` calls `session.open()`; `MyPlugin.term()` calls `session.close()`. All components receive `session` via constructor injection — no module-level globals, no implicit shared state.

### 3.3 Action Registry — explicit over implicit

The original plugin registered actions as **import side effects** (`callbacks/__init__.py` imports modules that call `action_manager.register(...)` at module top-level). The rewrite uses an explicit `ActionRegistry` class with all 27 actions listed in a single `_build_actions` method, with lazy imports to break circular dependencies.

---

## 4. Repository Layout

```
HexRaysPyTools/                                ← repo root
├── pyproject.toml                             ← build + test + lint config
├── README.md
├── LICENSE
├── CHANGELOG.md
├── .gitignore
├── .python-version                            ← "3.11"
├── ida-plugin.json                            ← HCLI manifest (at root)
│
├── src/
│   └── hexrays_pytools/                       ← Python package
│       ├── __init__.py                        ← __version__, __all__
│       ├── __main__.py                        ← PLUGIN_ENTRY
│       ├── plugin.py                          ← class HexRaysPyToolsPlugin
│       ├── session.py                         ← Session dataclass
│       ├── settings.py                        ← ida-settings wrapper
│       ├── logging_setup.py
│       ├── domain/                            ← Layer 3
│       │   ├── types/                         (tinfo_utils, func_type, udt_builder)
│       │   ├── scanner/                       (visitor_base, scanned_object, ctree_utils, member_extractor)
│       │   ├── recon/                         (member, discovered_vtable, structure_model, workspace)
│       │   ├── browser/                       (registered_class, registered_vtable, tree_model, proxy_model)
│       │   ├── xrefs/                         (xref_storage)
│       │   ├── graph/                         (structure_graph)
│       │   ├── templated/                     (templated_types, data/templated_types.toml)
│       │   ├── til/                           (type_library)
│       │   ├── ctree/                         (recast, rename, swap_if, negative_offsets)
│       │   └── actions/                       (action, registry, hx_callback, hx_events, +27 action files)
│       ├── infra/                             ← Layer 2
│       │   ├── ida_api/                       (hexrays, typeinf, name, ui)
│       │   ├── idb/                           (netnode)
│       │   ├── arch/                          (arch)
│       │   └── logging.py
│       ├── pure/                              ← Layer 1
│       │   ├── name_mangle.py
│       │   ├── scoring.py
│       │   ├── toml_template.py
│       │   └── result.py
│       └── ui/                                ← Layer 5
│           ├── widgets/                       (structure_builder, class_viewer, graph_viewer)
│           └── chooser.py
│
├── tests/
│   ├── conftest.py                            ← IDA API mock fixtures
│   ├── fixtures/
│   ├── pure/
│   ├── domain/
│   └── infra/
│
├── tools/
│   ├── build_plugin.py                        ← build ZIP, output to dist/
│   ├── hexrays_pytools_entry.py               ← HCLI entry stub template
│   └── mock_ida.py                            ← mock IDA Python modules
│
├── dist/                                      ← build artifacts (gitignored)
│
└── docs/
    ├── superpowers/specs/
    ├── architecture.md
    └── migration-from-v1.md
```

### 4.1 File naming

- `snake_case` for all `.py` files (PEP 8)
- Sub-package naming convention: **singular** for conceptual units (`scanner/`, `browser/`, `ctree/`, `recon/`, `til/`), **plural** for collections of items (`actions/`, `xrefs/`).
- Sub-package `__init__.py` are empty (use explicit imports for traceability)
- `hexrays_pytools_entry.py` lives at repo root (HCLI entry stub)

### 4.2 File mapping from original


| Original (6567 LOC)                  | New                                                      | Notes                                  |
| ------------------------------------ | -------------------------------------------------------- | -------------------------------------- |
| `HexRaysPyTools.py` (50)             | `__main__.py` + `plugin.py`                              | Separate entry point from plugin class |
| `settings.py` (75)                   | `settings.py`                                            | Uses `ida_settings` package (HCLI)     |
| `api.py` (579)                       | `scanner/visitor_base.py` + `scanner/scanned_object.py`  | Split two concerns                     |
| `forms.py` (404)                     | `ui/widgets/*` + `ui/chooser.py`                         | Fix `FormToPyQtWidget`                 |
| `core/cache.py` (72)                 | `recon/workspace.py` + `session.py`                      | Globals → Session fields               |
| `core/classes.py` (618)              | `browser/*` (4 files)                                    | Split 4 classes; fix QRegExp           |
| `core/common.py` (121)               | `pure/name_mangle.py`                                    | Pure-layer extraction                  |
| `core/const.py` (60)                 | `infra/ida_api/typeinf.py` + `session.py`                | Constants vs runtime init              |
| `core/helper.py` (435)               | Split into 6 files: `domain/types/{tinfo_utils,func_type,udt_builder}.py`, `domain/ctree/ctree_utils.py`, `infra/idb/netnode.py`, `infra/arch/arch.py` | God module → focused modules           |
| `core/structure_graph.py` (191)      | `graph/structure_graph.py`                               | Set-based DFS, `logger.warning`        |
| `core/struct_xrefs.py` (109)         | `xrefs/xref_storage.py`                                  | Netnode-backed                         |
| `core/temporary_structure.py` (1073) | Split into 4 files                                       | 1073-line file → 4 focused files       |
| `core/templated_types.py` (65)       | `templated/templated_types.py` + `pure/toml_template.py` | `tomllib`, validation                  |
| `core/type_library.py` (72)          | `til/type_library.py`                                    | Remove ctypes FFI                      |
| `core/variable_scanner.py` (337)     | `scanner/member_extractor.py`                            | Remove globals                         |
| `callbacks/*` (16 files)             | `ctree/*` + `actions/*`                                  | Split by concern                       |
| `types/templated_types.toml`         | `domain/templated/data/templated_types.toml`             | Move into package data                 |


---

## 5. Packaging (HCLI)

### 5.1 `ida-plugin.json` (HCLI manifest)

```json
{
  "$schema": "https://hcli.docs.hex-rays.com/schemas/ida-plugin.json",
  "IDAMetadataDescriptorVersion": 1,
  "plugin": {
    "name": "hexrays_pytools",
    "entryPoint": "hexrays_pytools_entry.py",
    "version": "2.0.0",
    "idaVersions": ["9.0", "9.1", "9.2"],
    "description": "Comprehensive toolkit for Hex-Rays decompiler: structure reconstruction, class/vtable management, code manipulation, and field cross-reference tracking.",
    "license": "MIT",
    "categories": ["ui-ux-and-visualization", "decompiler"],
    "pythonDependencies": [],
    "platforms": ["windows-x86_64", "linux-x86_64", "macos-aarch64"],
    "urls": {
      "repository": "https://github.com/EliteClassRoom/HexRaysPyTools"
    },
    "authors": [
      {"name": "Original Authors (see LICENSE)", "email": "noreply@example.com"},
      {"name": "Rewrite Maintainer", "email": "you@example.com"}
    ],
    "keywords": [
      "hex-rays", "decompiler", "ctree",
      "structure-reconstruction", "class-reconstruction",
      "vtable", "reverse-engineering"
    ],
    "settings": [
      {"key": "log_level", "type": "string", "required": false, "default": "INFO",
       "name": "Log Level", "choices": ["DEBUG", "INFO", "WARNING", "ERROR"],
       "documentation": "Python logging level for the plugin's logger.", "prompt": true},
      {"key": "propagate_through_all_names", "type": "boolean", "required": false, "default": false,
       "name": "Propagate Through All Names",
       "documentation": "If true, Name Propagation visits all names; otherwise only default names (v1, a2, this, field_*).",
       "prompt": true},
      {"key": "store_xrefs", "type": "boolean", "required": false, "default": true,
       "name": "Store Cross-References",
       "documentation": "Persist struct field cross-references in the IDB between sessions.",
       "prompt": true},
      {"key": "scan_any_type", "type": "boolean", "required": false, "default": false,
       "name": "Scan Any Variable Type",
       "documentation": "Allow scanning of variables of any type; otherwise only basic types (DWORD, QWORD, void*, ...).",
       "prompt": true},
      {"key": "templated_types_file", "type": "string", "required": false, "default": "",
       "name": "Custom Templated Types TOML",
       "documentation": "Absolute path to a TOML file with C++ templated types. Empty uses bundled default.",
       "prompt": false}
    ]
  }
}
```

### 5.2 Entry stub

The `hexrays_pytools_entry.py` file is a 15-line stub loaded by HCLI. It ensures the bundled `hexrays_pytools/` package is on `sys.path` and re-exports `PLUGIN_ENTRY` from `__main__.py`.

```python
# hexrays_pytools_entry.py
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from hexrays_pytools.__main__ import PLUGIN_ENTRY  # noqa: E402

__all__ = ["PLUGIN_ENTRY"]
```

### 5.3 Archive structure

```
hexrays_pytools-2.0.0.zip
├── ida-plugin.json
├── hexrays_pytools_entry.py
├── LICENSE
├── README.md
└── hexrays_pytools/            ← bundled source (full src/hexrays_pytools/)
    └── ...
```

Source distribution: the ZIP bundles the full source package. No PyPI publishing required.

### 5.4 Build script — `tools/build_plugin.py`

Reads version from `pyproject.toml`, creates a ZIP archive in `dist/` containing:

- `ida-plugin.json` (from repo root)
- `hexrays_pytools_entry.py` (from `tools/`)
- `LICENSE` and `README.md` (from repo root)
- Bundled `hexrays_pytools/` package (from `src/hexrays_pytools/`)

Validates that the resulting archive has `ida-plugin.json` at root and that `entryPoint` field matches a real file in the archive.

### 5.5 `pyproject.toml` essentials

- Build backend: `hatchling`
- Python: `>=3.11`
- Test framework: `pytest` with `--cov-fail-under=80`
- Lint: `ruff` + `mypy --strict`
- No runtime dependencies (IDA ships its own Python; `tomllib` in stdlib)

---

## 6. Feature Inventory &amp; Parity

### 6.1 27 actions (user-facing)


| #   | Class                        | Hotkey                                | New file                                                        | Phase |
| --- | ---------------------------- | ------------------------------------- | --------------------------------------------------------------- | ----- |
| 1   | ShallowScanVariable          | `F`                                   | `actions/scanners.py`                                           | P4    |
| 2   | DeepScanVariable             | `Shift+Alt+F`                         | `actions/scanners.py`                                           | P4    |
| 3   | RecognizeShape               | —                                     | `actions/scanners.py`                                           | P4    |
| 4   | DeepScanReturn               | —                                     | `actions/scanners.py`                                           | P4    |
| 5   | DeepScanFunctions            | —                                     | `actions/scanners.py`                                           | P4    |
| 6   | ShowStructureBuilder         | `Alt+F8`                              | `actions/form_requests.py`                                      | P4    |
| 7   | ShowGraph                    | `G`                                   | `actions/form_requests.py`                                      | P4    |
| 8   | ShowClasses                  | `Alt+F1`                              | `actions/form_requests.py`                                      | P4    |
| 9   | RecastItemLeft               | `Shift+L`                             | `ctree/recast.py` + `actions/recast_action.py`                  | P5    |
| 10  | RecastItemRight              | `Shift+R`                             | `ctree/recast.py` + `actions/recast_action.py`                  | P5    |
| 11  | RenameOther                  | `Ctrl+N`                              | `ctree/rename.py` + `actions/rename_action.py`                  | P5    |
| 12  | RenameInside                 | `Shift+N`                             | `ctree/rename.py` + `actions/rename_action.py`                  | P5    |
| 13  | RenameOutside                | `Ctrl+Shift+N`                        | `ctree/rename.py` + `actions/rename_action.py`                  | P5    |
| 14  | RenameMemberFromFunctionName | **changed to `Ctrl+Alt+N`** (fix B10) | `ctree/rename.py` + `actions/rename_action.py`                  | P5    |
| 15  | RenameUsingAssert            | —                                     | `ctree/rename.py` + `actions/rename_action.py`                  | P5    |
| 16  | PropagateName                | `P`                                   | `ctree/rename.py` + `actions/rename_action.py`                  | P5    |
| 17  | ConvertToUsercall            | —                                     | `actions/function_signature.py`                                 | P4    |
| 18  | AddRemoveReturn              | —                                     | `actions/function_signature.py`                                 | P4    |
| 19  | RemoveArgument               | —                                     | `actions/function_signature.py`                                 | P4    |
| 20  | CreateNewField               | `Ctrl+F`                              | `actions/struct_creation.py`                                    | P4    |
| 21  | CreateVtable                 | `V`                                   | `actions/virtual_table.py`                                      | P4    |
| 22  | GetStructureBySize           | —                                     | `actions/structs_by_size.py`                                    | P4    |
| 23  | SelectContainingStructure    | —                                     | `ctree/negative_offsets.py` + `actions/containing_structure.py` | P5    |
| 24  | ResetContainingStructure     | —                                     | `ctree/negative_offsets.py` + `actions/containing_structure.py` | P5    |
| 25  | FindFieldXrefs               | `Ctrl+X`                              | `actions/struct_xref.py`                                        | P4    |
| 26  | SwapThenElse                 | `Shift+Alt+S`                         | `ctree/swap_if.py` + `actions/swap_if_action.py`                | P5    |
| 27  | GuessAllocation              | —                                     | `actions/guess_allocation.py`                                   | P4    |


### 6.2 4 event handlers


| #   | Class                      | Event                        | New file               | Phase |
| --- | -------------------------- | ---------------------------- | ---------------------- | ----- |
| 28  | MemberDoubleClick          | `hxe_double_click`           | `actions/hx_events.py` | P4    |
| 29  | PotentialNegativeCollector | `hxe_maturity/CMAT_BUILT`    | `actions/hx_events.py` | P4    |
| 30  | StructXrefCollector        | `hxe_maturity/CMAT_FINAL`    | `actions/hx_events.py` | P4    |
| 31  | SilentIfSwapper            | `hxe_maturity/CMAT_TRANS1+2` | `actions/hx_events.py` | P4    |


**Total: 31 features** (27 actions + 4 event handlers). Feature parity is a hard requirement.

### 6.3 Naming collision fix

The original has two classes named `VirtualTable` with different semantics:

- `core/temporary_structure.VirtualTable` — a vtable **discovered** during scanning (working copy)
- `core/classes.VirtualTable` — a vtable **registered** in Local Types (registered view)

The rewrite renames them:

- `domain/recon/discovered_vtable.py` → `DiscoveredVTable`
- `domain/browser/registered_vtable.py` → `RegisteredVTable`

---

## 7. Implementation Phases


| Phase                          | Deliverable                                                                                                                                 | Test gate                                                                  |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **P0 — Foundation**            | `pure/` module (4 files + tests)                                                                                                            | `pytest tests/pure/` 100% pass                                             |
| **P1 — Infrastructure**        | `infra/`, `session.py`, `settings.py`, `plugin.py`, `__main__.py`                                                                           | IDA loads empty plugin, `pytest tests/infra/` pass                         |
| **P2 — Core domain (no Qt)**   | `domain/types/`, `domain/scanner/`, `domain/recon/` (except Qt model), `domain/xrefs/`, `domain/templated/`, `domain/til/`, `domain/graph/` | `pytest tests/domain/` ≥85% coverage on most modules                       |
| **P3 — Browser &amp; UI**      | `domain/browser/`, `ui/`, `domain/recon/structure_model.py` (Qt)                                                                            | Visual smoke test in IDA + `pytest` with `QT_QPA_PLATFORM=offscreen`       |
| **P4 — Actions &amp; wiring**  | `domain/actions/` (registry, hx_callback, hx_events, 27 actions)                                                                            | All 31 features register &amp; appear in correct widget                    |
| **P5 — Ctree manipulation**    | `domain/ctree/recast.py`, `rename.py`, `swap_if.py`, `negative_offsets.py`, plus 6 action files                                             | All 31 features work in manual smoke test                                  |
| **P6 — Polish &amp; bugfixes** | Type hints, mypy strict, ruff clean, CHANGELOG, migration doc                                                                               | `mypy --strict` pass, `ruff check` pass, `pytest --cov-fail-under=80` pass |


**Estimated effort:** 23–25 working days for a developer familiar with both IDA API and Qt. 30–50% additional budget if Hex-Rays SDK or PySide6 is new to the implementer.

### 7.1 MVP definition

After P0 + P1 + P2 + minimal P3 (just `ui/chooser.py` + `domain/recon/structure_model.py` Qt model, deferred full `widgets/structure_builder.py` to P3-final) — approximately 2 weeks of focused work — the deliverable is:

- IDA 9.x loads the plugin via HCLI without errors
- Structure reconstruction works (shallow scan + structure builder)
- Templated types view loads
- 5–6 core hotkeys work: `F`, `Shift+Alt+F`, `Alt+F8`, `Ctrl+X`, `Alt+F1`
- Tests pass for `pure/`, `domain/types/`, `domain/recon/` (non-Qt parts)

---

## 8. Bug Fixes (in scope of rewrite)

14 known bugs from the original codebase, all to be fixed:


| #   | Bug                                                         | File in original                                                          | Fix in new code                               | Phase   |
| --- | ----------------------------------------------------------- | ------------------------------------------------------------------------- | --------------------------------------------- | ------- |
| B1  | `FormToPyQtWidget` used when PySide6 imports                | `forms.py:36, 330`                                                        | `FormToPySideWidget`                          | P3      |
| B2  | `QRegExp.indexIn` (Qt4/Qt5 API removed in Qt6)              | `classes.py:354, 616`                                                     | `re.search`                                   | P3      |
| B3  | `setFilterRegExp` (Qt5 API renamed in Qt6)                  | `classes.py:602, 605`                                                     | `setFilterRegularExpression`                  | P3      |
| B4  | `sys.platform == "linux2"` (Py2-only, dead in Py3)          | `type_library.py:16`                                                      | `sys.platform == "linux"`                     | P2      |
| B5  | `logger.warn(...)` (deprecated Py3.7+)                      | `structure_graph.py:78`, others                                           | `logger.warning`                              | P2 + P6 |
| B6  | `visited_downward/upward` as `list` (O(n²))                 | `structure_graph.py:48-49`                                                | `set`                                         | P2      |
| B7  | `idaapi.remove_pointer` deprecated                          | `struct_xref_representation.py:44`                                        | `tinfo.remove_ptr_or_array()`                 | P4      |
| B8  | `hx_view.refresh_ctext()` removed                           | `swap_if.py:84`                                                           | `hx_view.refresh_view(True)`                  | P5      |
| B9  | `"Recast Return to ".format(...)` missing placeholder       | `recasts.py:149`                                                          | `"Recast Return to {}".format(...)`           | P5      |
| B10 | Ctrl+N hotkey conflict                                      | `renames.py:35, 164`                                                      | `RenameMemberFromFunctionName` → `Ctrl+Alt+N` | P5      |
| B11 | Global mutable state (4 locations)                          | `cache.py`, `variable_scanner.py`, `classes.py`, `temporary_structure.py` | `Session` + DI                                | P1–P3   |
| B12 | `XrefStorage` uses `idc.create_array` (legacy API)          | `struct_xrefs.py`                                                         | Netnode storage with auto-migration           | P2      |
| B13 | `class Foo(object):` Py2-style inheritance (10 occurrences) | Multiple                                                                  | Plain `class Foo:`                            | P6      |
| B14 | Bare `print()` debug statements                             | Multiple files                                                            | `logger.debug()` via `infra/logging.py`       | P6      |


---

## 9. Test Strategy


| Layer             | Test approach         | Tool                                 | Target coverage |
| ----------------- | --------------------- | ------------------------------------ | --------------- |
| `pure/`           | Unit test, no IDA     | pytest                               | 100%            |
| `infra/`          | Unit + mock IDA       | pytest + `tools/mock_ida.py`         | 90%             |
| `domain/types/`   | Unit + mock IDA       | pytest                               | 85%             |
| `domain/scanner/` | Unit with cfunc mock  | pytest                               | 70%             |
| `domain/recon/`   | Unit + Qt offscreen   | pytest + `QT_QPA_PLATFORM=offscreen` | 75%             |
| `domain/browser/` | Unit + Qt offscreen   | pytest                               | 80%             |
| `domain/ctree/`   | Unit with cfunc mock  | pytest                               | 60%             |
| `domain/actions/` | Manual smoke in IDA   | manual                               | 50%             |
| `ui/`             | Widget test offscreen | pytest                               | 40%             |


**Global gate:** `pytest --cov-fail-under=80` enforced in CI.

**Manual smoke tests:** Performed in real IDA 9.x during P3, P4, P5, P6. The implementer must have a working IDA 9.x installation to verify behavior.

---

## 10. Risk Register


| ID  | Risk                                              | Probability | Impact | Mitigation                                                                 |
| --- | ------------------------------------------------- | ----------- | ------ | -------------------------------------------------------------------------- |
| R1  | IDA 9.0/9.1/9.2 API differences                   | Medium      | Medium | Manual smoke test on all 3 versions; document workarounds                  |
| R2  | `ida_settings` package maturity                   | Medium      | Medium | Wrapper interface → easy to swap implementation                            |
| R3  | ctree scan behavior changes between IDA versions  | High        | High   | Visual regression test on a curated sample binary                          |
| R4  | 27 features × manual test = time sink             | High        | Medium | Sample binary covering all 27 cases; automate as much as possible          |
| R5  | Existing user resistance to hotkey change         | Low         | Low    | CHANGELOG clearly states `Ctrl+N` → `Ctrl+Alt+N`; `Ctrl+Alt+N` is adjacent |
| R6  | XrefStorage data migration loses data             | Medium      | High   | Auto-migrate; backup before deleting old array                             |
| R7  | Build script error → HCLI doesn't load            | Low         | High   | Test `hcli plugin lint` after build; verify `entryPoint` path              |
| R8  | `mock_ida.py` insufficient for some tests         | High        | Medium | Per-test functional mocks; accept some tests need real IDA                 |
| R9  | Effort underestimation (real 35–40 days vs 23–25) | Medium      | Medium | Phase gates allow stopping/adjusting; MVP at week 2                        |
| R10 | No IDA 9.x available to the implementer           | Unknown     | High   | Confirm early; use IDA trial/evaluation if needed                          |


---

## 11. Decision Log


| #   | Decision                                                          | Rationale                                                       |
| --- | ----------------------------------------------------------------- | --------------------------------------------------------------- |
| D1  | Rewrite toàn diện (not just repackage)                            | User selected "Rewrite toàn diện"                               |
| D2  | IDA 9.x only                                                      | User selected "IDA 9.x only (khuyến nghị)"                      |
| D3  | 100% feature parity                                               | User selected "Tất cả tính năng (parity)"                       |
| D4  | Unit tests với mock                                               | User selected "Unit tests với mock"                             |
| D5  | src/ + pyproject + dist/ layout                                   | User selected this layout                                       |
| D6  | Package name `hexrays_pytools` (snake_case); HCLI plugin `name` is `hexrays_pytools`; IDA plugin display name (`wanted_name` in `plugin.py`) is `HexRaysPyTools` (CamelCase preserved) | PEP 8 compliance for Python identifier; preserve brand name in IDA's plugin manager UI |
| D7  | Source distribution (no PyPI)                                     | Simpler for v2.0.0; PyPI possible in v2.1+                      |
| D8  | idaVersions `["9.0", "9.1", "9.2"]`                               | Cover entire current 9.x range                                  |
| D9  | Hotkey `Ctrl+N` → `Ctrl+Alt+N` for `RenameMemberFromFunctionName` | Fix B10 conflict; keep `Ctrl+N` for the more-used `RenameOther` |
| D10 | Auto-migrate XrefStorage from array to netnode                    | Preserve existing user data                                     |
| D11 | 80% strict coverage gate                                          | Enforce quality in CI                                           |
| D12 | `ida_settings` stdlib (HCLI package)                              | Official HCLI mechanism                                         |
| D13 | pytest + mock for UI                                              | CI-friendly; manual smoke in real IDA                           |
| D14 | 1 action = 1 file (16 files for 27 actions)                       | Per-feature isolation, easy review                              |
| D15 | Spec doc location: `docs/superpowers/specs/`                      | Per brainstorming skill default                                 |


---

## 12. Open Questions

Items that should be confirmed before starting Phase 0:

1. **License** — what is the original license? Is it MIT-compatible? Rewrite inherits or replaces?
2. **Original author attribution** — do we list original authors in `ida-plugin.json`? Get email consent?
3. **Repository URL** — where will the rewrite live? (Existing GitHub repo? New fork?)
4. **Sample test binary** — do we have a small binary (~5 MB) that exercises all 27 features? Needed for P4–P5 manual testing.
5. **IDA 9.x availability** — does the implementer have access to a real IDA 9.x installation? Critical for smoke tests.
6. `**is_legal_type` heuristic** — the agent's analysis noted a comment "after 9.0 nearly always returns False". This is a known broken heuristic that may need re-implementation. Confirm or defer?

---

## 13. References

- HCLI plugin packaging spec: [https://hcli.docs.hex-rays.com/reference/plugin-packaging-and-format/](https://hcli.docs.hex-rays.com/reference/plugin-packaging-and-format/)
- Original plugin source: `refs/HexRaysPyTools/`
- 5-layer architecture rationale: see Section 3.1

