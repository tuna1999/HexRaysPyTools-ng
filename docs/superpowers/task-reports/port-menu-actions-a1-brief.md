# Phase A.1 Brief: Port `core/const.py` (tinfo singletons)

**Date:** 2026-06-19
**Phase:** A.1 of port-menu-actions research
**Goal:** Create `src/hexrays_pytools/domain/const.py` and wire it into Session.

## Source

`refs/HexRaysPyTools/HexRaysPyTools/core/const.py` (60 LOC).

## What's ported

- `Consts` dataclass with 16 fields (all the tinfo singletons + EA64/EA_SIZE/LEGAL_TYPES)
- `init_consts()` factory that builds them for the current IDA session
- Add `consts: Consts | None = None` field to `Session`
- Wire `init_consts()` into `Session._init_caches()`

## Why a dataclass, not module-level globals

The original plugin uses module-level globals — this is the **B11 bug** in the
CHANGELOG ("module-level globals (cache, classes, etc.)"). A `Consts` dataclass
stored on the Session:

- Honors the Session-based architecture already in place
- Makes the data lifetime explicit (created in `Session.open()`, garbage
  collected on `Session.close()`)
- Makes the constants testable (you can construct a `Consts` directly)

The `init_consts()` factory still depends on `idaapi` (real or mocked), so it
must be called from inside IDA — but the `Consts` dataclass itself is pure
data and can be inspected/asserted in tests.

## File map

- `src/hexrays_pytools/domain/const.py` (NEW) — Consts dataclass + init_consts
- `src/hexrays_pytools/domain/session.py` (MODIFIED) — add `consts` field
- `tests/domain/test_const.py` (NEW) — test init_consts + field shape

## Field names (mapping original → new)

| Original module global | New `Consts` field |
|---|---|
| `EA64` | `ea64: bool` |
| `EA_SIZE` | `ea_size: int` |
| `VOID_TINFO` | `void_tinfo: tinfo_t` |
| `PVOID_TINFO` | `pvoid_tinfo: tinfo_t` |
| `CONST_VOID_TINFO` | `const_void_tinfo: tinfo_t` |
| `CONST_PVOID_TINFO` | `const_pvoid_tinfo: tinfo_t` |
| `CHAR_TINFO` | `char_tinfo: tinfo_t` |
| `PCHAR_TINFO` | `pchar_tinfo: tinfo_t` |
| `CONST_PCHAR_TINFO` | `const_pchar_tinfo: tinfo_t` |
| `BYTE_TINFO` | `byte_tinfo: tinfo_t` |
| `PBYTE_TINFO` | `pbyte_tinfo: tinfo_t` |
| `WORD_TINFO` | `word_tinfo: tinfo_t` |
| `PWORD_TINFO` | `pword_tinfo: tinfo_t` |
| `X_WORD_TINFO` | `x_word_tinfo: tinfo_t` |
| `PX_WORD_TINFO` | `px_word_tinfo: tinfo_t` |
| `DUMMY_FUNC` | `dummy_func: tinfo_t` |
| `LEGAL_TYPES` | `legal_types: list[tinfo_t]` |

## Tests

1. `test_consts_dataclass_exists` — `Consts` is importable and instantiable
   with a constructed `idaapi.tinfo_t` (under mock).
2. `test_init_consts_returns_consts` — `init_consts()` returns a `Consts`
   instance with all 16 fields set (non-None for tinfo fields).
3. `test_init_consts_sets_ea64` — `ea64` field reflects `idaapi.inf_is_64bit()`.
4. `test_session_open_populates_consts` — `Session.open()` calls
   `init_consts()` and stores result in `session.consts`.
5. `test_session_consts_default_none` — A fresh `Session()` has `consts=None`.

## Quality gates

- `pytest tests/domain/test_const.py tests/domain/test_session.py` — pass
- `mypy --strict src/hexrays_pytools/domain/const.py` — clean
- `ruff check src/hexrays_pytools/domain/const.py` — clean
- Full suite (`pytest`) — still passes
