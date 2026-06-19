# Tasks 6.5 + 7.1-7.7 Batched: Polish + Release

## Context

Final phase: write CHANGELOG, create release artifacts (ida-plugin.json, README, LICENSE, docs), build script, tag v2.0.0.

## Files to Create

### Task 6.5: CHANGELOG.md (project root)

```markdown
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
```

### Task 7.1: ida-plugin.json (project root)

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
      "repository": "https://github.com/yourname/HexRaysPyTools"
    },
    "authors": [
      {"name": "Original Authors", "email": "noreply@example.com"},
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
       "documentation": "Python logging level.", "prompt": true},
      {"key": "propagate_through_all_names", "type": "boolean", "required": false, "default": false,
       "name": "Propagate Through All Names",
       "documentation": "If true, Name Propagation visits all names; otherwise only default names.", "prompt": true},
      {"key": "store_xrefs", "type": "boolean", "required": false, "default": true,
       "name": "Store Cross-References",
       "documentation": "Persist struct field xrefs in the IDB between sessions.", "prompt": true},
      {"key": "scan_any_type", "type": "boolean", "required": false, "default": false,
       "name": "Scan Any Variable Type",
       "documentation": "Allow scanning of variables of any type; otherwise only basic types.", "prompt": true},
      {"key": "templated_types_file", "type": "string", "required": false, "default": "",
       "name": "Custom Templated Types TOML",
       "documentation": "Absolute path to a TOML file with C++ templated types. Empty uses bundled default.",
       "prompt": false}
    ]
  }
}
```

### Task 7.2: README.md (project root, replaces existing stub)

```markdown
# HexRaysPyTools

Comprehensive toolkit for IDA Pro's Hex-Rays decompiler: structure reconstruction, class/vtable management, code manipulation, and field cross-reference tracking.

## Installation

The plugin is distributed as an HCLI archive. See [CHANGELOG.md](CHANGELOG.md) for the v2.0.0 release.

```bash
# After running tools/build_plugin.py to produce dist/hexrays_pytools-2.0.0.zip:
hcli plugin install dist/hexrays_pytools-2.0.0.zip
```

## Requirements

- IDA Pro 9.0, 9.1, or 9.2
- Python 3.11+
- PySide6

## Features

- **Structure reconstruction** — Shallow/Deep scan, Recognize Shape, Deep Scan Return, Deep Scan Functions
- **Class/vtable management** — Show Classes, Show Graph, Set First Argument Type, Commit
- **Code manipulation** — Recast (Shift+L, Shift+R), Rename (Ctrl+N, Shift+N, Ctrl+Shift+N, Ctrl+Alt+N), Swap If/Else (Shift+Alt+S)
- **Field cross-references** — Find Field Xrefs (Ctrl+X), shown in Structure Builder

See [docs/architecture.md](docs/architecture.md) for the internal design.

## Development

```bash
pip install -e ".[dev]"
pytest -v
mypy --strict src/hexrays_pytools/
ruff check src/hexrays_pytools/ tests/ tools/
```

See [docs/superpowers/specs/2026-06-18-hexrays-pytools-rewrite-design.md](docs/superpowers/specs/2026-06-18-hexrays-pytools-rewrite-design.md) for the rewrite design rationale.
```

### Task 7.2 cont: Copy LICENSE from refs/

Copy `D:\re_dev_projects\ida-plugins\HexRaysPyTools\refs\HexRaysPyTools\readme.md` references the original license; if no LICENSE file exists, create one with MIT text. If a LICENSE file is in `refs/`, copy it. Otherwise:

```markdown
MIT License

Copyright (c) 2016-2024 Original Authors
Copyright (c) 2026 Rewrite Maintainer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Task 7.4: docs/architecture.md

```markdown
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
```

### Task 7.4 cont: docs/migration-from-v1.md

```markdown
# Migration from v1.x

v2.0.0 is a complete rewrite. Most user-facing functionality is preserved, but with a few changes:

## Settings
- Settings are now stored via HCLI ida-settings (no more `.cfg` file)
- 5 settings with same keys: `log_level`, `propagate_through_all_names`, `store_xrefs`, `scan_any_type`, `templated_types_file`
- Configure via `hcli plugin config` instead of editing the `.cfg` file

## Hotkeys
- One hotkey change: `RenameMemberFromFunctionName` moved from `Ctrl+N` to `Ctrl+Alt+N` to avoid collision with `RenameOther` (which still uses `Ctrl+N`)

## Storage
- Struct field xrefs are now stored in IDA netnodes (not `idc.create_array`)
- Auto-migrate from v1.x format on first load (one-time)

## No code changes required for end users
If you just use the plugin interactively, no code changes are needed.
```

### Task 7.5: tools/build_plugin.py

```python
"""Build HCLI-installable ZIP archive of the plugin."""
from __future__ import annotations
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "hexrays_pytools"
DIST = ROOT / "dist"
ENTRY_STUB = ROOT / "tools" / "hexrays_pytools_entry.py"


def main() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    version = pyproject["project"]["version"]
    archive = DIST / f"hexrays_pytools-{version}.zip"
    DIST.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(ROOT / "ida-plugin.json", "ida-plugin.json")
        zf.write(ENTRY_STUB, "hexrays_pytools_entry.py")
        zf.write(ROOT / "LICENSE", "LICENSE")
        zf.write(ROOT / "README.md", "README.md")
        for f in SRC.rglob("*"):
            if f.is_file():
                arcname = "hexrays_pytools" / f.relative_to(SRC)
                zf.write(f, arcname)
    print(f"Built: {archive}  ({archive.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
```

## Verification (each task)

```bash
# 6.5
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG.md for v2.0.0"

# 7.1
python -c "import json; json.load(open('ida-plugin.json'))"

# 7.2
git add README.md
git commit -m "docs: add README.md (HCLI install + dev instructions)"

# 7.4
git add docs/architecture.md docs/migration-from-v1.md
git commit -m "docs: add architecture + migration guides"

# 7.5
python tools/build_plugin.py
git add tools/build_plugin.py dist/
git commit -m "feat(tooling): add build_plugin.py (HCLI ZIP build)"

# Final
git tag v2.0.0
```

## Final Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-6.5-7.7-report.md`

After all work, return:
- All commit SHAs
- Tag v2.0.0
- Test summary
- Final coverage %
- Path to built ZIP
- Path to report