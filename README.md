# HexRaysPyTools-ng

Comprehensive toolkit for IDA Pro's Hex-Rays decompiler: structure reconstruction, class/vtable management, code manipulation, and field cross-reference tracking.

This is a fork of [HexRaysPyTools](https://github.com/igogo-x86/hexrayspytools) (originally by igogo-x86) and [oopsmishap/HexRaysPyTools](https://github.com/oopsmishap/HexRaysPyTools), rewritten to focus on **IDA 9.x** and **Qt6 (PySide6)** support.

## Installation

The plugin is distributed as an HCLI archive.

```bash
# After running tools/build_plugin.py to produce dist/hexrays_pytools_ng-1.0.0.zip:
hcli plugin install dist/hexrays_pytools_ng-1.0.0.zip
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

The Structure Builder combines repeated ordinary field accesses to the same offset and type into one
candidate while retaining their scan origins. Different types at an offset remain
separate candidates for conflict resolution.

Array lengths use the distance to the next retained field (a heuristic).
A trailing array without a known bound is exported as a flexible array
(`items[]`); its fixed length cannot be recovered from dynamic indexing alone.

Deep Scan follows calls with known destinations; indirect calls are not
recursed into.

See [docs/architecture.md](docs/architecture.md) for the internal design.

## Development

```bash
pip install -e ".[dev]"
pytest -v
mypy --strict src/hexrays_pytools/
ruff check src/hexrays_pytools/ tests/ tools/
```

