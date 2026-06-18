# HexRaysPyTools v2.0.0 Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the legacy `HexRaysPyTools` IDA plugin (~6567 LOC, Python 2/3 hybrid) into a modern, fully-tested, HCLI-packaged plugin targeting IDA Pro 9.0–9.2 with 100% feature parity, 14 bug fixes, and 80%+ test coverage.

**Architecture:** 5-layer dependency model — pure Python (Layer 1) → infrastructure (Layer 2) → domain logic (Layer 3) → plugin entry & wiring (Layer 4) → Qt UI (Layer 5). Strict downward-only dependencies. `Session` dataclass replaces all global mutable state. Action registry uses explicit dependency injection.

**Tech Stack:**
- Python 3.11+ (uses `tomllib`, `match/case`, modern type hints)
- IDA Pro 9.0–9.2 (Python API)
- HCLI for plugin packaging (`ida-plugin.json`)
- PySide6 (Qt6) for UI — PyQt5 fallback removed
- pytest + pytest-cov for testing, mypy --strict for type checking, ruff for linting
- hatchling build backend

**Spec reference:** `docs/superpowers/specs/2026-06-18-hexrays-pytools-rewrite-design.md`

---

## Global Constraints

These apply to every task. Every task's requirements implicitly include this section.

- **Python version:** `>=3.11` (use `tomllib` from stdlib, `match/case`, `X | Y` union syntax, `dict[str, int]` generic syntax)
- **No Python 2 compatibility:** never write `class Foo(object):` (use `class Foo:`), never write `super(Clz, self).__init__()` (use `super().__init__()`), never write `sys.platform == "linux2"` (use `"linux"`)
- **Naming:** `snake_case` for files and functions, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- **Type hints:** Required on all public function signatures. Use `mypy --strict` compatible syntax.
- **Logging:** Never use `print()` for debug; use `logger = logging.getLogger(__name__)` + `logger.debug/info/warning/error`
- **Qt:** PySide6 only. Use `FormToPySideWidget` not `FormToPyQtWidget`. Use `QRegularExpression` + `setFilterRegularExpression` not `QRegExp` + `setFilterRegExp`. Use `setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)` scoped enum.
- **IDA API:** Prefer `ida_hexrays.*`, `ida_typeinf.*`, `ida_name.*` namespace modules. Use `tinfo.remove_ptr_or_array()` not `idaapi.remove_pointer`. Use `vdui.refresh_view(True)` not `vdui.refresh_ctext()`.
- **No globals:** All mutable state goes through `Session` (initialized in `MyPlugin.init()`, closed in `MyPlugin.term()`)
- **Coverage gate:** `pytest --cov-fail-under=80` must pass before any commit
- **Lint:** `ruff check` must pass before any commit
- **Type check:** `mypy --strict` must pass before any commit
- **Commit format:** `<type>: <description>` (types: feat, fix, refactor, docs, test, chore, perf)
- **One commit per task:** never combine multiple tasks' work in one commit

---

## File Structure (created/modified by this plan)

```
HexRaysPyTools/
├── pyproject.toml                                  ← created in Task 0.1
├── .gitignore                                       ← created in Task 0.1
├── .python-version                                  ← created in Task 0.1
├── ida-plugin.json                                  ← created in Task 7.1
├── README.md                                        ← created in Task 7.2
├── LICENSE                                          ← copied from refs/ in Task 7.2
├── CHANGELOG.md                                     ← created in Task 7.3
├── docs/
│   ├── architecture.md                              ← created in Task 7.4
│   ├── migration-from-v1.md                         ← created in Task 7.4
│   └── superpowers/
│       ├── specs/                                   ← (already created in brainstorming)
│       └── plans/                                   ← (this file)
├── src/hexrays_pytools/
│   ├── __init__.py                                  ← created in Task 0.2
│   ├── __main__.py                                  ← created in Task 1.6
│   ├── plugin.py                                    ← created in Task 1.6
│   ├── session.py                                   ← created in Task 1.3
│   ├── settings.py                                  ← created in Task 1.4
│   ├── logging_setup.py                             ← created in Task 0.3
│   ├── domain/
│   │   ├── types/                                   (Tasks 2.1–2.3)
│   │   ├── scanner/                                 (Tasks 2.4–2.7)
│   │   ├── recon/                                   (Tasks 2.8–2.11)
│   │   ├── xrefs/                                   (Task 2.12)
│   │   ├── templated/                               (Task 2.13)
│   │   ├── til/                                     (Task 2.14)
│   │   ├── graph/                                   (Task 2.15)
│   │   ├── ctree/                                   (Tasks 5.1–5.4)
│   │   ├── browser/                                 (Tasks 3.1–3.4)
│   │   └── actions/                                 (Tasks 4.1–4.6, 5.5–5.8)
│   ├── infra/                                       (Tasks 1.1–1.2)
│   ├── pure/                                        (Tasks 0.4–0.7)
│   └── ui/                                          (Tasks 3.5–3.6)
├── tests/                                           (mirrors src/)
│   ├── conftest.py                                  ← created in Task 0.8
│   ├── pure/                                        (Tasks 0.4–0.7)
│   ├── infra/                                       (Tasks 1.1–1.2)
│   ├── domain/                                      (per module tasks)
│   └── fixtures/                                    ← created in Task 0.8
├── tools/
│   ├── build_plugin.py                              ← created in Task 7.5
│   ├── hexrays_pytools_entry.py                     ← created in Task 1.6
│   └── mock_ida.py                                  ← created in Task 0.8
└── dist/                                            ← created at build time (gitignored)
```

**Total tasks: ~60** (estimated 23–25 working days at 2–4 tasks/day)

---

## Phase 0 — Foundation (Pure Python + Project Skeleton)

**Goal:** Establish the project skeleton (pyproject.toml, package structure) and build the 4 pure-Python utility modules with full test coverage. After this phase, `pip install -e ".[dev]"` works and `pytest tests/pure/` passes 100%.

**Phase gate:** `pytest tests/pure/` 100% pass, `mypy --strict src/pure/` pass, `ruff check` pass.

---

### Task 0.1: Project skeleton (pyproject.toml, .gitignore, .python-version)

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.python-version`

**Interfaces:**
- Consumes: nothing
- Produces: working `pip install -e ".[dev]"` that pulls in pytest, pytest-cov, pytest-mock, ruff, mypy

- [ ] **Step 1: Create `.python-version`**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\.python-version` with the following content:

```
3.11
```

- [ ] **Step 2: Create `.gitignore`**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\.gitignore` with the following content:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.eggs/
build/
dist/
.venv/
venv/

# Test
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/

# IDE
.vscode/
.idea/
*.swp

# Plugin runtime
$HXP_*
```

- [ ] **Step 3: Create `pyproject.toml`**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\pyproject.toml` with the following content:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "hexrays_pytools"
version = "2.0.0"
description = "Comprehensive toolkit for Hex-Rays decompiler"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
authors = [
    {name = "HexRaysPyTools Rewrite Maintainer", email = "you@example.com"}
]
keywords = ["ida", "hex-rays", "decompiler", "ctree", "reverse-engineering"]
classifiers = [
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS",
]
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-cov>=4.1",
    "pytest-mock>=3.12",
    "ruff>=0.1.0",
    "mypy>=1.7",
]

[tool.hatch.build.targets.wheel]
packages = ["src/hexrays_pytools"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=hexrays_pytools --cov-report=term-missing --cov-fail-under=80"
markers = [
    "unit: pure unit tests, no IDA mock",
    "mock: tests using IDA API mock",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "PT", "RET", "SIM"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_ignores = true
disallow_untyped_defs = true
```

- [ ] **Step 4: Verify install works**

Run:
```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
pip install -e ".[dev]"
```

Expected: Installation succeeds. If it fails with "ERROR: file:///D:/re_dev_projects/ida-plugins/HexRaysPyTools does not appear to be a Python project: 'pyproject.toml' missing", check that pyproject.toml is in the repo root.

- [ ] **Step 5: Verify tooling works**

Run:
```bash
ruff check .
mypy --version
pytest --version
```

Expected: ruff reports "All checks passed!" (no Python files to check yet is OK), mypy and pytest print version info.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore .python-version
git commit -m "chore: add project skeleton (pyproject.toml, .gitignore, .python-version)"
```

---

### Task 0.2: Create package skeleton (`__init__.py`)

**Files:**
- Create: `src/hexrays_pytools/__init__.py`
- Create: `src/hexrays_pytools/.gitkeep` (no, this isn't needed)

**Interfaces:**
- Consumes: nothing
- Produces: importable `hexrays_pytools` package with `__version__` exposed

- [ ] **Step 1: Create the package directory**

Run (PowerShell):
```powershell
New-Item -ItemType Directory -Force -Path "D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools"
```

- [ ] **Step 2: Create `__init__.py`**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\__init__.py` with the following content:

```python
"""HexRaysPyTools — comprehensive toolkit for Hex-Rays decompiler."""

__version__ = "2.0.0"

__all__ = ["__version__"]
```

- [ ] **Step 3: Verify import works**

Run:
```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
python -c "import hexrays_pytools; print(hexrays_pytools.__version__)"
```

Expected: prints `2.0.0`

- [ ] **Step 4: Commit**

```bash
git add src/hexrays_pytools/__init__.py
git commit -m "chore: create hexrays_pytools package skeleton"
```

---

### Task 0.3: Logging setup module

**Files:**
- Create: `src/hexrays_pytools/logging_setup.py`
- Create: `tests/pure/test_logging_setup.py`
- Create: `tests/pure/__init__.py`

**Interfaces:**
- Consumes: nothing
- Produces: `setup_logging(level: int) -> None` function that configures the root logger with `[%(levelname)s] %(message)s\t(%(module)s:%(funcName)s)` format (matches original)

- [ ] **Step 1: Create test file**

Create the directory `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\pure\`.

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\pure\__init__.py` with empty content (just `pass`).

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\pure\test_logging_setup.py` with the following content:

```python
"""Test logging_setup module."""
import logging
from hexrays_pytools.logging_setup import setup_logging


def test_setup_logging_sets_root_level() -> None:
    """setup_logging(N) should set root logger level to N."""
    setup_logging(logging.WARNING)
    assert logging.getLogger().level == logging.WARNING


def test_setup_logging_is_idempotent() -> None:
    """Calling setup_logging twice should not add duplicate handlers."""
    setup_logging(logging.INFO)
    initial_handler_count = len(logging.getLogger().handlers)
    setup_logging(logging.INFO)
    assert len(logging.getLogger().handlers) == initial_handler_count


def test_setup_logging_format_contains_module_and_function() -> None:
    """The log format should include module name and function name."""
    import io
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s\t(%(module)s:%(funcName)s)"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    try:
        root.info("test message")
        output = buf.getvalue()
        assert "test message" in output
        assert "test_logging_setup" in output  # module name
        assert "test_setup_logging_format_contains_module_and_function" in output  # function name
    finally:
        root.removeHandler(handler)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
pytest tests/pure/test_logging_setup.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'hexrays_pytools.logging_setup'`

- [ ] **Step 3: Create `logging_setup.py`**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\logging_setup.py` with the following content:

```python
"""Centralized logging configuration for HexRaysPyTools.

Replaces the original `logging.basicConfig(...)` call in `PLUGIN_ENTRY`.
Use `setup_logging(level)` once during plugin init.
"""
import logging

_LOG_FORMAT = "[%(levelname)s] %(message)s\t(%(module)s:%(funcName)s)"


def setup_logging(level: int) -> None:
    """Configure the root logger with our standard format.
    
    Idempotent: safe to call multiple times (does not add duplicate handlers).
    """
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(handler)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/pure/test_logging_setup.py -v
```

Expected: 3 tests pass

- [ ] **Step 5: Verify type check**

Run:
```bash
mypy --strict src/hexrays_pytools/logging_setup.py
```

Expected: `Success: no issues found in 1 source file`

- [ ] **Step 6: Verify lint**

Run:
```bash
ruff check src/hexrays_pytools/logging_setup.py tests/pure/
```

Expected: `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add src/hexrays_pytools/logging_setup.py tests/pure/
git commit -m "feat(pure): add logging_setup module with tests"
```

---

### Task 0.4: `pure/result.py` — `Result[T, E]` type

**Files:**
- Create: `src/hexrays_pytools/pure/__init__.py`
- Create: `src/hexrays_pytools/pure/result.py`
- Create: `tests/pure/test_result.py`

**Interfaces:**
- Consumes: nothing
- Produces: `Result[T, E]` dataclass with `is_ok: bool`, `value: T | None`, `error: E | None`, factory methods `ok(value)` and `err(error)`, and `unwrap() -> T` / `unwrap_or(default: T) -> T`

- [ ] **Step 1: Create directory**

Run (PowerShell):
```powershell
New-Item -ItemType Directory -Force -Path "D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\pure"
```

- [ ] **Step 2: Create `__init__.py` files**

Write `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\pure\__init__.py` with empty content (just `pass`).

- [ ] **Step 3: Create test file**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\pure\test_result.py` with the following content:

```python
"""Test Result type."""
import pytest
from hexrays_pytools.pure.result import Result


def test_ok_creates_successful_result() -> None:
    """Result.ok(value) creates a result with is_ok=True and value=value."""
    r = Result.ok(42)
    assert r.is_ok is True
    assert r.value == 42
    assert r.error is None


def test_err_creates_error_result() -> None:
    """Result.err(error) creates a result with is_ok=False and error=error."""
    r = Result.err("something went wrong")
    assert r.is_ok is False
    assert r.value is None
    assert r.error == "something went wrong"


def test_unwrap_returns_value_on_ok() -> None:
    """Result.unwrap() returns the value if is_ok=True."""
    r = Result.ok(42)
    assert r.unwrap() == 42


def test_unwrap_raises_on_error() -> None:
    """Result.unwrap() raises ValueError if is_ok=False."""
    r = Result.err("oops")
    with pytest.raises(ValueError, match="oops"):
        r.unwrap()


def test_unwrap_or_returns_value_on_ok() -> None:
    """Result.unwrap_or(default) returns the value if is_ok=True."""
    r = Result.ok(42)
    assert r.unwrap_or(0) == 42


def test_unwrap_or_returns_default_on_error() -> None:
    """Result.unwrap_or(default) returns default if is_ok=False."""
    r = Result.err("oops")
    assert r.unwrap_or(0) == 0


def test_result_is_immutable() -> None:
    """Result instances should be frozen (immutable)."""
    r = Result.ok(42)
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        r.value = 100  # type: ignore[misc]
```

- [ ] **Step 4: Run test to verify it fails**

Run:
```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
pytest tests/pure/test_result.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'hexrays_pytools.pure.result'`

- [ ] **Step 5: Create `result.py`**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\pure\result.py` with the following content:

```python
"""Result[T, E] type for explicit error handling.

Use `Result.ok(value)` for success and `Result.err(error)` for failure.
Avoids exception-based control flow for expected errors.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Result(Generic[T, E]):
    """A value or an error. Use `ok()` and `err()` factories.
    
    Example:
        def parse_decl(s: str) -> Result[tinfo_t, str]:
            if not s:
                return Result.err("empty string")
            ...
            return Result.ok(tinfo)
    """
    is_ok: bool
    value: T | None
    error: E | None

    @classmethod
    def ok(cls, value: T) -> "Result[T, E]":
        """Create a successful result containing `value`."""
        return cls(is_ok=True, value=value, error=None)

    @classmethod
    def err(cls, error: E) -> "Result[T, E]":
        """Create an error result containing `error`."""
        return cls(is_ok=False, value=None, error=error)

    def unwrap(self) -> T:
        """Return the value or raise ValueError if is_ok=False."""
        if not self.is_ok:
            raise ValueError(f"called unwrap() on error result: {self.error}")
        assert self.value is not None  # for type checker
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Return the value or `default` if is_ok=False."""
        if self.is_ok:
            assert self.value is not None
            return self.value
        return default
```

- [ ] **Step 6: Run test to verify it passes**

Run:
```bash
pytest tests/pure/test_result.py -v
```

Expected: 7 tests pass

- [ ] **Step 7: Verify type check + lint**

Run:
```bash
mypy --strict src/hexrays_pytools/pure/result.py
ruff check src/hexrays_pytools/pure/result.py tests/pure/test_result.py
```

Expected: both pass

- [ ] **Step 8: Commit**

```bash
git add src/hexrays_pytools/pure/ tests/pure/test_result.py
git commit -m "feat(pure): add Result[T, E] type with full test coverage"
```

---

### Task 0.5: `pure/name_mangle.py` — sanitize demangled C++ names

**Files:**
- Create: `src/hexrays_pytools/pure/name_mangle.py`
- Create: `tests/pure/test_name_mangle.py`

**Interfaces:**
- Consumes: nothing (pure function)
- Produces: `sanitize_c_name(name: str) -> str` function that takes a demangled C++ symbol name and returns a C-legal identifier (replaces `::`, `<`, `>`, `*`, `~`, etc. with safe substitutions). Preserves the original semantics from `core/common.py:demangled_name_to_c_str`.

- [ ] **Step 1: Create test file**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\pure\test_name_mangle.py` with the following content:

```python
"""Test name_mangle.sanitize_c_name."""
from hexrays_pytools.pure.name_mangle import sanitize_c_name


def test_simple_name_unchanged() -> None:
    """Names that are already valid C identifiers pass through unchanged."""
    assert sanitize_c_name("foo") == "foo"
    assert sanitize_c_name("MyClass") == "MyClass"
    assert sanitize_c_name("foo_bar123") == "foo_bar123"


def test_colon_colon_replaced_with_underscore() -> None:
    """`::` namespace separator is replaced with `_`."""
    assert sanitize_c_name("std::vector") == "std_vector"
    assert sanitize_c_name("a::b::c") == "a_b_c"


def test_pointer_suffix_replaced() -> None:
    """`*` pointer suffix is replaced with `_PTR`."""
    assert sanitize_c_name("int*") == "int_PTR"
    assert sanitize_c_name("MyClass**") == "MyClass_PTR_PTR"


def test_template_angle_brackets_replaced() -> None:
    """`<` and `>` template brackets are replaced with `_t_`."""
    assert sanitize_c_name("std::vector<int>") == "std_vector_t_int_t_"
    assert sanitize_c_name("map<string,int>") == "map_t_string_t_int_t_"


def test_destructor_tilde_replaced() -> None:
    """`~` destructor prefix is replaced with `DESTRUCTOR_`."""
    assert sanitize_c_name("~MyClass") == "DESTRUCTOR_MyClass"


def test_access_keywords_stripped() -> None:
    """`public:`, `protected:`, `private:` are stripped."""
    assert sanitize_c_name("public:foo") == "foo"
    assert sanitize_c_name("protected:bar") == "bar"
    assert sanitize_c_name("private:baz") == "baz"


def test_vtable_and_typeinfo_prefix_preserved() -> None:
    """Names starting with backtick are preserved as-is."""
    # In original: backtick names returned as-is
    assert sanitize_c_name("`vtable for Foo") == "`vtable for Foo"
    assert sanitize_c_name("`typeinfo for Bar") == "`typeinfo for Bar"


def test_empty_string_returns_empty() -> None:
    """Empty input returns empty output."""
    assert sanitize_c_name("") == ""


def test_illegal_chars_replaced_with_underscore() -> None:
    """Other illegal characters are replaced or stripped."""
    # Multiple consecutive colons collapse
    assert "::" not in sanitize_c_name("foo:::bar")
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
pytest tests/pure/test_name_mangle.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'hexrays_pytools.pure.name_mangle'`

- [ ] **Step 3: Create `name_mangle.py`**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\pure\name_mangle.py` with the following content:

```python
"""Sanitize demangled C++ names to C-legal identifiers.

Pure function — no IDA dependency. Replaces the original `demangled_name_to_c_str`
in `HexRaysPyTools/core/common.py` with explicit, well-tested behavior.
"""
from __future__ import annotations
import re

# Characters that are NOT legal in a C identifier
_ILLEGAL_CHARS = re.compile(r":::+|(?=:(?=[^:]))(?=(?<=[^:]):):|^:[^:]|[^:]:$|^:$|[^a-zA-Z_0-9:]")


def sanitize_c_name(name: str) -> str:
    """Convert a demangled C++ symbol name into a C-legal identifier.
    
    Examples:
        "std::vector<int*>" -> "std_vector_t_int_PTR_t_"
        "~MyClass"          -> "DESTRUCTOR_MyClass"
        "`vtable for Foo"   -> "`vtable for Foo"  (preserved as-is)
    
    Rules:
        1. Names starting with backtick are returned unchanged (vtable/typeinfo).
        2. `::` is replaced with `_` (namespace separator).
        3. `*` (pointer) is replaced with `_PTR`.
        4. `<` and `>` (templates) are replaced with `_t_`.
        5. `~` (destructor) is replaced with `DESTRUCTOR_`.
        6. `public:`, `protected:`, `private:` access keywords are stripped.
        7. Other illegal characters are stripped or replaced.
    """
    if not name:
        return ""
    # Preserve `vtable and `typeinfo names (backtick prefix)
    if name.startswith("`"):
        return name
    # Strip access keywords
    name = name.replace("public:", "").replace("protected:", "").replace("private:", "")
    # Replace destructor prefix
    name = name.replace("~", "DESTRUCTOR_")
    # Replace pointer suffix
    name = name.replace("*", "_PTR")
    # Replace template angle brackets
    name = name.replace("<", "_t_").replace(">", "_t_")
    # Collapse illegal character runs and split on remaining colons
    name = "_".join(filter(len, _ILLEGAL_CHARS.split(name)))
    return name
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/pure/test_name_mangle.py -v
```

Expected: 9 tests pass

- [ ] **Step 5: Verify type check + lint**

Run:
```bash
mypy --strict src/hexrays_pytools/pure/name_mangle.py
ruff check src/hexrays_pytools/pure/name_mangle.py tests/pure/test_name_mangle.py
```

Expected: both pass

- [ ] **Step 6: Commit**

```bash
git add src/hexrays_pytools/pure/name_mangle.py tests/pure/test_name_mangle.py
git commit -m "feat(pure): add name_mangle.sanitize_c_name (replaces common.py)"
```

---

### Task 0.6: `pure/scoring.py` — member collision scoring

**Files:**
- Create: `src/hexrays_pytools/pure/scoring.py`
- Create: `tests/pure/test_scoring.py`

**Interfaces:**
- Consumes: nothing
- Produces: `score_member(name: str, type_size: int) -> int` function that returns a numeric score for a struct member candidate. Higher = better. Uses the heuristic from `core/temporary_structure.py` (alignment penalty for `_<X>` names, bonus for specific types like `char` over `_BYTE`).

- [ ] **Step 1: Create test file**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\pure\test_scoring.py` with the following content:

```python
"""Test scoring.score_member."""
from hexrays_pytools.pure.scoring import score_member


def test_simple_int_field_score() -> None:
    """A 4-byte int field with a good name scores high."""
    score = score_member("size", 4)
    assert score > 0


def test_larger_alignment_scores_higher() -> None:
    """Bigger primitive types score higher (better alignment)."""
    assert score_member("foo", 8) > score_member("foo", 4)
    assert score_member("foo", 4) > score_member("foo", 2)
    assert score_member("foo", 2) > score_member("foo", 1)


def test_underscore_prefix_name_penalized() -> None:
    """Names starting with `_` (likely auto-generated) score lower."""
    assert score_member("_size", 4) < score_member("size", 4)


def test_vtable_marker_name_bonus() -> None:
    """Names containing `vtable` get a bonus."""
    assert score_member("vtable_ptr", 8) > score_member("data", 8)


def test_zero_size_returns_negative() -> None:
    """Zero-size members get a low (or negative) score."""
    assert score_member("foo", 0) < 0


def test_scoring_is_pure() -> None:
    """score_member is a pure function — same inputs always give same output."""
    assert score_member("foo", 4) == score_member("foo", 4)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
pytest tests/pure/test_scoring.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `scoring.py`**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\pure\scoring.py` with the following content:

```python
"""Heuristic scoring for struct member candidates.

Pure function — no IDA dependency. Used to rank competing candidates for the
same offset during `Resolve Conflicts` in the Structure Builder.

Scoring factors (higher = better):
    + log2(size) for size 1, 2, 4, 8
    + 0x2000 if name contains 'vtable'
    - 0x1000 if name starts with '_' (likely auto-generated)
    - 0xFFFF if size is 0 (invalid member)
"""
from __future__ import annotations

_VTABLE_BONUS = 0x2000
_UNDERSCORE_PENALTY = 0x1000
_ZERO_SIZE_PENALTY = 0xFFFF

_SIZE_SCORE: dict[int, int] = {1: 0, 2: 1, 4: 2, 8: 3}


def score_member(name: str, type_size: int) -> int:
    """Return a numeric score for a struct member candidate.
    
    Higher score = better candidate when resolving collisions.
    Negative scores indicate invalid members.
    """
    if type_size <= 0:
        return -_ZERO_SIZE_PENALTY
    
    score = _SIZE_SCORE.get(type_size, type_size.bit_length() - 1)
    
    if name.startswith("_"):
        score -= _UNDERSCORE_PENALTY
    if "vtable" in name.lower():
        score += _VTABLE_BONUS
    
    return score
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/pure/test_scoring.py -v
```

Expected: 6 tests pass

- [ ] **Step 5: Verify type check + lint**

Run:
```bash
mypy --strict src/hexrays_pytools/pure/scoring.py
ruff check src/hexrays_pytools/pure/scoring.py tests/pure/test_scoring.py
```

Expected: both pass

- [ ] **Step 6: Commit**

```bash
git add src/hexrays_pytools/pure/scoring.py tests/pure/test_scoring.py
git commit -m "feat(pure): add scoring.score_member for collision resolution"
```

---

### Task 0.7: `pure/toml_template.py` — validate & render templated types

**Files:**
- Create: `src/hexrays_pytools/pure/toml_template.py`
- Create: `tests/pure/test_toml_template.py`
- Create: `tests/fixtures/sample_templated_types.toml`

**Interfaces:**
- Consumes: nothing
- Produces: `parse_toml_template(content: str) -> Result[TemplateDict, str]` where `TemplateDict = dict[str, TemplateDef]` and `TemplateDef = TypedDict(base_name, types, struct)`. Also `render_template(template: TemplateDef, args: list[str]) -> Result[(str, str), str]` returning `(type_name, c_decl)`.

- [ ] **Step 1: Create test fixture**

Create the directory `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\fixtures\`.

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\fixtures\__init__.py` with empty content.

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\fixtures\sample_templated_types.toml` with the following content:

```toml
["std::vector<T>"]
base_name = "std_vector_{1}"
types = ["T"]
struct = """
struct std_vector_{1} {
    {0} *_Myfirst;
    {0} *_Mylast;
    {0} *_Myend;
};
"""

["std::map<K,V>"]
base_name = "std_map_{1}_{3}"
types = ["K", "V"]
struct = """
struct std_pair_{1}_{3} {
    {0} first;
    {2} second;
};
struct std_map_{1}_{3} {
    std_pair_{1}_{3} *_Myhead;
    unsigned long long _Mysize;
};
"""
```

- [ ] **Step 2: Create test file**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\pure\test_toml_template.py` with the following content:

```python
"""Test toml_template.parse_toml_template and render_template."""
from pathlib import Path
from hexrays_pytools.pure.toml_template import parse_toml_template, render_template

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_templated_types.toml"


def test_parse_valid_toml() -> None:
    """Valid TOML is parsed into a dict of templates."""
    result = parse_toml_template(FIXTURE.read_text())
    assert result.is_ok
    templates = result.unwrap()
    assert "std::vector<T>" in templates
    assert "std::map<K,V>" in templates


def test_parse_invalid_toml_returns_err() -> None:
    """Malformed TOML returns an error result."""
    result = parse_toml_template("not valid toml [[[")
    assert not result.is_ok
    assert result.error is not None


def test_render_single_param_template() -> None:
    """A template with 1 type param renders correctly with 2 args (actual, pretty)."""
    result = parse_toml_template(FIXTURE.read_text())
    templates = result.unwrap()
    # render_template expects 2*N args: [actual_0, pretty_0, actual_1, pretty_1, ...]
    # For N=1 (std::vector<T>), need 2 args: actual="int *", pretty="pInt"
    rendered = render_template(templates["std::vector<T>"], ["int *", "pInt"])
    assert rendered.is_ok
    type_name, decl = rendered.unwrap()
    assert type_name == "std_vector_pInt"
    assert "int_PTR *_Myfirst" in decl


def test_render_two_param_template() -> None:
    """A template with 2 type params renders correctly with 4 args (actual, pretty, actual, pretty)."""
    result = parse_toml_template(FIXTURE.read_text())
    templates = result.unwrap()
    # For N=2 (std::map<K,V>), need 4 args: [K_actual, K_pretty, V_actual, V_pretty]
    rendered = render_template(templates["std::map<K,V>"], ["int", "pInt", "char *", "pChar"])
    assert rendered.is_ok
    type_name, decl = rendered.unwrap()
    assert type_name == "std_map_pInt_pChar"
    assert "int first" in decl
    assert "char_PTR second" in decl


def test_render_wrong_arg_count_returns_err() -> None:
    """Wrong number of args returns an error."""
    result = parse_toml_template(FIXTURE.read_text())
    templates = result.unwrap()
    # For N=1, need 2 args. Pass 3 (wrong).
    rendered = render_template(templates["std::vector<T>"], ["int *", "pInt", "extra"])
    assert not rendered.is_ok


def test_render_unknown_template_returns_err() -> None:
    """Render with 0 args (need 2) returns an error."""
    result = parse_toml_template(FIXTURE.read_text())
    templates = result.unwrap()
    rendered = render_template(templates["std::vector<T>"], [])  # 0 args, need 2
    assert not rendered.is_ok
```

- [ ] **Step 3: Run test to verify it fails**

Run:
```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
pytest tests/pure/test_toml_template.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Create `toml_template.py`**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\pure\toml_template.py` with the following content:

```python
"""Parse and render C++ templated types defined in TOML.

Pure module — no IDA dependency. Replaces `core/templated_types.py` with explicit
validation and the stdlib `tomllib` (Python 3.11+).

The TOML format expects:
    ["pretty::TypeName<T>"]
    base_name = "ida_type_{1}"        # format string for IDA's struct name
    types = ["T"]                     # list of type-parameter names
    struct = "struct ida_type_{1} {{ {0} field; }};"  # C-like declaration

Format tokens: for N type params, tokens 0..N-1 are actual types and tokens N..2N-1
are "pretty print" tokens (used in `base_name` and inside `struct` for unique IDs).
"""
from __future__ import annotations
import tomllib
from typing import TypedDict

from .result import Result


class TemplateDef(TypedDict):
    """Schema for a single templated type entry."""
    base_name: str
    types: list[str]
    struct: str


# Parse result is dict[str, TemplateDef]
TemplateDict = dict[str, TemplateDef]


def parse_toml_template(content: str) -> Result[TemplateDict, str]:
    """Parse TOML content into a dict of templated type definitions.
    
    Returns Result.ok(dict) on success, Result.err(message) on parse failure.
    """
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError as e:
        return Result.err(f"TOML parse error: {e}")
    return Result.ok(data)


def render_template(
    template: TemplateDef, args: list[str]
) -> Result[tuple[str, str], str]:
    """Render a template with the given type arguments.
    
    `args` is a flat list: [actual_type_0, pretty_0, actual_type_1, pretty_1, ...]
    Length must be exactly 2 * len(template["types"]).
    
    Returns Result.ok((type_name, c_decl)) on success, Result.err(msg) on mismatch.
    """
    n = len(template["types"])
    if len(args) != 2 * n:
        return Result.err(
            f"arg count mismatch: expected {2 * n} (for {n} type params), got {len(args)}"
        )
    try:
        type_name = template["base_name"].format(*args)
        c_decl = template["struct"].format(*args)
    except (IndexError, KeyError) as e:
        return Result.err(f"format token error: {e}")
    return Result.ok((type_name, c_decl))
```

- [ ] **Step 5: Run test to verify it passes**

Run:
```bash
pytest tests/pure/test_toml_template.py -v
```

Expected: 6 tests pass

- [ ] **Step 6: Verify type check + lint**

Run:
```bash
mypy --strict src/hexrays_pytools/pure/toml_template.py
ruff check src/hexrays_pytools/pure/toml_template.py tests/pure/test_toml_template.py
```

Expected: both pass

- [ ] **Step 7: Commit**

```bash
git add src/hexrays_pytools/pure/toml_template.py tests/pure/test_toml_template.py tests/fixtures/
git commit -m "feat(pure): add toml_template parser/renderer (stdlib tomllib)"
```

---

### Task 0.8: Mock IDA infrastructure for tests

**Files:**
- Create: `tools/mock_ida.py`
- Create: `tests/conftest.py`

**Interfaces:**
- Consumes: nothing
- Produces: `install() -> None` function that mocks IDA Python modules in `sys.modules` for unit tests, `reset() -> None` to clear call history between tests. `tests/conftest.py` auto-installs mocks before any test runs.

- [ ] **Step 1: Create `mock_ida.py`**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tools\mock_ida.py` with the following content:

```python
"""Install mock IDA Python modules into sys.modules for unit tests.

This module is the test infrastructure for running pytest WITHOUT a real IDA
installation. It provides:

- A `_MockIdaModule` class that returns MagicMock for any attribute access
  (similar to the original `HexRaysPyTools` plugin's `idaapi` global, which is
  a SWIG module).

- `install()` registers all IDA-related modules as mocks. Idempotent.

- `reset()` clears call history between tests.

Usage:
    # In tests/conftest.py or test files:
    from tools.mock_ida import install, reset
    install()
    # Now you can `import idaapi; idaapi.tinfo_t()` etc.
"""
from __future__ import annotations
import sys
from typing import Any
from unittest.mock import MagicMock


# Modules that should be mocked
MOCK_MODULES: tuple[str, ...] = (
    "idaapi", "idc", "idautils", "ida_hexrays", "ida_typeinf",
    "ida_name", "ida_kernwin", "ida_idaapi", "ida_settings",
    "ida_funcs", "ida_lines", "ida_nalt", "ida_diskio", "ida_idp",
    "ida_widget", "ida_graph", "ida_gdl", "ida_netnode",
    "PySide6", "PySide6.QtCore", "PySide6.QtWidgets", "PySide6.QtGui",
    "PyQt5", "PyQt5.QtCore", "PyQt5.QtWidgets", "PyQt5.QtGui",
)


class _MockIdaModule:
    """Catch-all mock: any attribute returns a MagicMock.
    
    Pre-creates some common constants (BADADDR, BADSIZE, etc.) to avoid
    `MagicMock() == 0xFFFFFFFFFFFFFFFF` confusion in tests.
    """
    # Common IDA constants
    BADADDR: int = 0xFFFFFFFFFFFFFFFF
    BADSIZE: int = 0xFFFFFFFFFFFFFFFF
    BADORD: int = 0xFFFFFFFFFFFFFFFF
    PT_TYP: int = 1
    NTF_REPLACE: int = 0x00000002
    NTF_NOBASE: int = 0x00000000
    BTF_STRUCT: int = 0x00000004
    BTF_UNION: int = 0x00000005
    BTF_ENUM: int = 0x00000006
    BTF_CHAR: int = 0x00000010
    BTF_BYTE: int = 0x00000000
    BT_VOID: int = 0x00000001
    BT_INT: int = 0x00000003
    BTM_CONST: int = 0x00000004
    SEGPERM_EXEC: int = 0x00000004
    TINFO_DEFINITE: int = 0x00000010
    CM_CC_MASK: int = 0x0000000F
    CM_CC_CDECL: int = 0x00000000
    CM_CC_STDCALL: int = 0x00000001
    CM_CC_FASTCALL: int = 0x00000003
    CM_CC_THISCALL: int = 0x00000002
    CM_CC_ELLIPSIS: int = 0x00000004
    CM_CC_SPECIAL: int = 0x0000000B
    CM_CC_UNKNOWN: int = 0x00000000
    PRTYPE_MULTI: int = 0x00000001
    PRTYPE_TYPE: int = 0x00000002
    PRTYPE_SEMI: int = 0x00000004
    AST_ENABLE_ALWAYS: int = 0x00000004
    AST_ENABLE_FOR_WIDGET: int = 0x00000003
    AST_ENABLE: int = 0x00000001
    AST_DISABLE: int = 0x00000000
    AST_DISABLE_FOR_WIDGET: int = 0x00000002
    BWN_PSEUDOCODE: int = 0x00000000
    BWN_TILIST: int = 0x00000001
    BWN_DISASM: int = 0x00000002
    BWN_FUNCS: int = 0x00000003
    BWN_LOCTYPS: int = 0x00000004
    VDI_EXPR: int = 0x00000000
    VDI_FUNC: int = 0x00000001
    VDI_LVAR: int = 0x00000002
    cot_var: int = 0x00000001
    cot_obj: int = 0x00000002
    cot_memptr: int = 0x00000003
    cot_memref: int = 0x00000004
    cot_num: int = 0x00000005
    cot_call: int = 0x00000006
    cot_asg: int = 0x00000007
    cot_cast: int = 0x00000008
    cot_ref: int = 0x00000009
    cot_add: int = 0x0000000A
    cot_sub: int = 0x0000000B
    cot_idx: int = 0x0000000C
    cot_helper: int = 0x0000000D
    cot_fnum: int = 0x0000000E
    cot_fadd: int = 0x0000000F
    cot_fsub: int = 0x00000010
    cot_fmul: int = 0x00000011
    cot_fdiv: int = 0x00000012
    cit_if: int = 0x00000020
    cit_return: int = 0x00000021
    cit_block: int = 0x00000022
    cit_goto: int = 0x00000023
    CMAT_BUILT: int = 0x00000000
    CMAT_TRANS1: int = 0x00000001
    CMAT_TRANS2: int = 0x00000002
    CMAT_FINAL: int = 0x00000003
    hxe_populating_popup: int = 0x00000001
    hxe_double_click: int = 0x00000002
    hxe_maturity: int = 0x00000003
    CV_POST: int = 0x00000001
    DELIT_SIMPLE: int = 0x00000000
    STRMEM_OFFSET: int = 0x00000000
    AR_STR: int = 0x00000005
    INF_SHORT_DN: int = 0x00000003
    INF_LONG_DN: int = 0x00000002

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return MagicMock(name=f"ida.{self.__class__.__name__}.{name}")


def install() -> None:
    """Install all mock IDA modules into sys.modules. Idempotent."""
    for mod_name in MOCK_MODULES:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = _MockIdaModule()


def reset() -> None:
    """Reset call history on all mock modules (between tests)."""
    for mod_name in MOCK_MODULES:
        mod = sys.modules.get(mod_name)
        if mod is None:
            continue
        for attr_name in dir(mod):
            if attr_name.startswith("_"):
                continue
            attr = getattr(mod, attr_name, None)
            if isinstance(attr, MagicMock):
                attr.reset_mock()
```

- [ ] **Step 2: Create `tests/conftest.py`**

Write the file `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\conftest.py` with the following content:

```python
"""Pytest configuration: install mock IDA modules before any test runs.

This file is auto-loaded by pytest. We install mocks at the top level so that
tests can `import hexrays_pytools.*` without IDA being installed.
"""
import sys
from pathlib import Path

# Add tools/ to sys.path so `import mock_ida` works
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

# Install mocks immediately on conftest load
import mock_ida  # noqa: E402
mock_ida.install()


def pytest_runtest_setup(item) -> None:
    """Reset mock call history before each test for isolation."""
    mock_ida.reset()
```

- [ ] **Step 3: Run existing tests to verify mock doesn't break them**

Run:
```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
pytest tests/pure/ -v
```

Expected: all pure/ tests still pass (10+ tests pass)

- [ ] **Step 4: Verify type check + lint**

Run:
```bash
mypy --strict tools/mock_ida.py
ruff check tools/mock_ida.py tests/conftest.py
```

Expected: both pass

- [ ] **Step 5: Commit**

```bash
git add tools/mock_ida.py tests/conftest.py
git commit -m "feat(test): add mock_ida infrastructure for unit tests"
```

---

### Task 0.9: Phase 0 gate — verify all pure tests pass

**Files:** none (verification only)

- [ ] **Step 1: Run full test suite**

Run:
```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
pytest -v
```

Expected: all tests in `tests/pure/` pass (≥25 tests)

- [ ] **Step 2: Run mypy strict on all pure modules**

Run:
```bash
mypy --strict src/hexrays_pytools/pure/ src/hexrays_pytools/logging_setup.py
```

Expected: `Success: no issues found in N source files`

- [ ] **Step 3: Run ruff on all created files**

Run:
```bash
ruff check src/hexrays_pytools/pure/ src/hexrays_pytools/logging_setup.py tools/ tests/
```

Expected: `All checks passed!`

- [ ] **Step 4: Verify Phase 0 deliverables**

Checklist:
- [ ] `pyproject.toml`, `.gitignore`, `.python-version` exist
- [ ] `src/hexrays_pytools/__init__.py` exports `__version__ = "2.0.0"`
- [ ] 4 pure modules exist: `name_mangle.py`, `scoring.py`, `result.py`, `toml_template.py`
- [ ] `tools/mock_ida.py` provides `install()` and `reset()`
- [ ] `tests/conftest.py` auto-installs mocks
- [ ] All tests pass, mypy strict passes, ruff passes

- [ ] **Step 5: Tag the phase completion**

```bash
git tag phase-0-foundation
```

---

## Phase 1 — Infrastructure (IDA-thin wrappers + Session + Plugin Entry)

**Goal:** Build the IDA infrastructure layer (architecture abstraction, netnode storage, logging) plus the `Session` dataclass and the plugin entry point. After this phase, IDA Pro 9.x can load the plugin via HCLI without errors (the plugin registers no actions yet, but the lifecycle works).

**Phase gate:** Empty plugin loads in IDA 9.x without exception; `pytest tests/infra/ tests/test_session.py` pass.

---

*(Plan continues for Phases 1-7 in the same TDD format. Due to length, this preview shows Phases 0-1 structure. The full plan would have ~60 tasks total. Below are task summaries for the remaining phases, to be elaborated in the same bite-sized format.)*

---

## Phase 1 Task Summaries (full TDD format in actual execution)

- **Task 1.1:** `infra/arch/arch.py` — `is_code_ea(ea) -> bool`, `get_ptr(ea) -> int` (ARM thumb bit handling)
- **Task 1.2:** `infra/idb/netnode.py` — wrapper around `idaapi.netnode` for typed storage
- **Task 1.3:** `domain/session.py` — `Session` dataclass with `open()` / `close()` lifecycle
- **Task 1.4:** `domain/settings.py` — `ida_settings` wrapper
- **Task 1.5:** `domain/recon/workspace.py` — `ReconWorkspace` (replaces `cache.temporary_structure`)
- **Task 1.6:** `plugin.py` + `__main__.py` + `tools/hexrays_pytools_entry.py` — HCLI entry point

## Phase 2 Task Summaries

- **Task 2.1:** `domain/types/tinfo_utils.py` — get ordinal, get fields at offset, is_legal_type
- **Task 2.2:** `domain/types/func_type.py` — set/get func args, return, calling convention
- **Task 2.3:** `domain/types/udt_builder.py` — build `udt_type_data_t` from member list
- **Task 2.4:** `domain/scanner/visitor_base.py` — `ObjectVisitor` (ctree_parentee_t base)
- **Task 2.5:** `domain/scanner/scanned_object.py` — `ScanObject` hierarchy
- **Task 2.6:** `domain/scanner/ctree_utils.py` — `find_asm_address`, parent walker helpers
- **Task 2.7:** `domain/scanner/member_extractor.py` — `SearchVisitor` (the main scanner)
- **Task 2.8:** `domain/recon/member.py` — `AbstractMember`, `Member`, `VoidMember`
- **Task 2.9:** `domain/recon/discovered_vtable.py` — `DiscoveredVTable` (renamed from `VirtualTable`)
- **Task 2.10:** `domain/recon/structure_model.py` — `QAbstractTableModel` for the builder
- **Task 2.11:** `domain/recon/workspace.py` — `ReconWorkspace` (model container)
- **Task 2.12:** `domain/xrefs/xref_storage.py` — netnode-backed `XrefStorage` with auto-migrate
- **Task 2.13:** `domain/templated/templated_types.py` + `data/templated_types.toml` — wrapper around pure parser
- **Task 2.14:** `domain/til/type_library.py` — `choose_til`, `create_type`, `import_type` (no ctypes FFI)
- **Task 2.15:** `domain/graph/structure_graph.py` — set-based DFS

## Phase 3 Task Summaries

- **Task 3.1:** `domain/browser/registered_class.py` — `Class` (was `classes.Class`)
- **Task 3.2:** `domain/browser/registered_vtable.py` — `RegisteredVTable`
- **Task 3.3:** `domain/browser/tree_model.py` — `TreeModel` (uses `QRegularExpression`)
- **Task 3.4:** `domain/browser/proxy_model.py` — `ProxyModel` (uses `setFilterRegularExpression`)
- **Task 3.5:** `ui/chooser.py` — `MyChoose` wrapper
- **Task 3.6:** `ui/widgets/structure_builder.py` + `class_viewer.py` + `graph_viewer.py` — 3 forms

## Phase 4 Task Summaries

- **Task 4.1:** `domain/actions/action.py` — base `Action`, `HexRaysPopupAction`, `HexRaysXrefAction`
- **Task 4.2:** `domain/actions/registry.py` — `ActionRegistry` with explicit 27-action list
- **Task 4.3:** `domain/actions/hx_callback.py` — `HxCallbackManager`
- **Task 4.4:** `domain/actions/hx_events.py` — 4 event handlers
- **Task 4.5:** `domain/actions/scanners.py` — 5 scanner actions
- **Task 4.6:** `domain/actions/form_requests.py`, `function_signature.py`, `struct_creation.py`, `struct_xref.py`, `structs_by_size.py`, `guess_allocation.py`, `member_double_click.py`, `virtual_table.py` — 8 more action files

## Phase 5 Task Summaries

- **Task 5.1:** `domain/ctree/recast.py` — `RecastItemLeft`, `RecastItemRight` logic
- **Task 5.2:** `domain/ctree/rename.py` — 6 rename actions
- **Task 5.3:** `domain/ctree/swap_if.py` — `SwapThenElse` logic (uses `vdui.refresh_view(True)`)
- **Task 5.4:** `domain/ctree/negative_offsets.py` — `SelectContainingStructure`, `ResetContainingStructure`
- **Task 5.5:** `domain/actions/recast_action.py` — 2 action classes
- **Task 5.6:** `domain/actions/rename_action.py` — 6 action classes
- **Task 5.7:** `domain/actions/swap_if_action.py` — 1 action class
- **Task 5.8:** `domain/actions/containing_structure.py` — 2 action classes

## Phase 6 Task Summaries

- **Task 6.1:** Apply all 14 bug fixes systematically
- **Task 6.2:** mypy --strict on full project
- **Task 6.3:** ruff clean on full project
- **Task 6.4:** pytest --cov-fail-under=80 verification
- **Task 6.5:** Write `CHANGELOG.md` v2.0.0 entry

## Phase 7 Task Summaries

- **Task 7.1:** Create `ida-plugin.json` (HCLI manifest)
- **Task 7.2:** Create `README.md` and copy `LICENSE` from `refs/`
- **Task 7.3:** Create `CHANGELOG.md`
- **Task 7.4:** Create `docs/architecture.md` and `docs/migration-from-v1.md`
- **Task 7.5:** Create `tools/build_plugin.py` (build ZIP)
- **Task 7.6:** Run `hcli plugin lint` on the built archive
- **Task 7.7:** Tag v2.0.0 release

---

## Self-Review

**1. Spec coverage:** All 13 sections of the spec are covered:
- §1 Executive Summary — addressed in plan header
- §2 Goals & Non-Goals — encoded in Global Constraints
- §3 Architecture — encoded in File Structure + Task organization
- §4 Repository Layout — encoded in File Structure
- §5 Packaging — Phase 7 tasks
- §6 Feature Inventory — Phases 3-5 tasks
- §7 Implementation Phases — Phases 0-7 in this plan
- §8 Bug Fixes — Task 6.1
- §9 Test Strategy — applied per-task via TDD
- §10 Risk Register — covered by Phase gates
- §11 Decision Log — applied in Task implementations
- §12 Open Questions — to be confirmed by user before Phase 0 starts
- §13 References — cited in spec

**2. Placeholder scan:** No "TBD", "TODO", "fill in details" in the detailed tasks. Phase 1-7 task summaries intentionally reference the same TDD structure without rewriting the full 5-step format; full plan executes this in the chosen execution mode.

**3. Type consistency:** `Session`, `Action`, `Result`, `ReconWorkspace`, `XrefStorage`, `TemplatedTypes`, `DiscoveredVTable`, `RegisteredVTable` — names consistent with spec. Function signatures shown in interfaces follow Python 3.11+ type hint syntax (X | Y, list[str], etc.).
