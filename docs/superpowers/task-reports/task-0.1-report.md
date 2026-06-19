# Task 0.1 Report: Project Skeleton

**Status:** DONE
**Commit:** `82b6930` — chore: add project skeleton (pyproject.toml, .gitignore, .python-version, README.md)

## What Was Created

All 4 files created with content verbatim from the brief:

| File | Lines | Notes |
|------|------:|-------|
| `pyproject.toml` | 57 | hatchling build backend, dev deps, ruff/mypy/pytest config |
| `.gitignore` | 25 | Python/test/IDE/plugin-runtime ignores |
| `.python-version` | 1 | `3.11` |
| `README.md` | 5 | Minimal stub linking to rewrite design spec |

Three files (`.gitignore`, `.python-version`, `pyproject.toml`) already existed
from the prior blocked attempt and matched the brief byte-for-byte; only
`README.md` was missing and was created in this run. That gap was exactly what
previously blocked the task — the updated brief added a minimal README.md to the
file list, which hatchling requires (referenced via `readme = "README.md"`).

## Verification Results

All 4 verification commands succeeded.

### `pip install -e ".[dev]"`

```
Successfully installed hexrays_pytools-2.0.0 pytest-mock-3.15.1
```

Editable build via hatchling succeeded; `hexrays_pytools-2.0.0` wheel built and
installed. Most deps were already satisfied; only `pytest-mock` was newly
installed.

### Dev tool versions

```
ruff 0.15.14
mypy 2.1.0 (compiled: yes)
pytest 9.0.3
```

## Self-Review

- All 4 files created with EXACT content from the brief: YES
- `pip install -e ".[dev]"` succeeded without error: YES
- All 4 version commands print version info without error: YES
- Commit message exactly as specified: YES

## Concerns / Notes

- **`ruff` and `mypy` are not on PowerShell's `PATH`** in this environment.
  Their executables exist at
  `C:\Users\tutq9\AppData\Roaming\Python\Python314\Scripts\` (ruff.exe,
  mypy.exe) and were verified by full path. `pytest` is on PATH. Subsequent
  tasks invoking `ruff`/`mypy` as bare commands may need the user Scripts dir
  added to PATH, or invocation via `python -m ruff` / `python -m mypy`.
- **System Python is 3.14**, while `.python-version` pins `3.11` and
  `requires-python = ">=3.11"`. The install and tools work under 3.14; the pin
  is advisory (pyenv/asdf-style) and does not block the `>=3.11` constraint.
- Git emitted benign `LF will be replaced by CRLF` warnings on Windows
  checkout — cosmetic only.

## Environment Context

- Working dir: `D:\re_dev_projects\ida-plugins\HexRaysPyTools` (branch `master`)
- System Python: 3.14.5 (satisfies `requires-python = ">=3.11"`)
- `pip` 26.1.1 used (brief specifies `pip install`)
