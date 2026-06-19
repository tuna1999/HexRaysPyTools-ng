# Task 0.1 Brief: Project Skeleton

## Where This Fits

This is the **first task** of the HexRaysPyTools v2.0.0 rewrite project. It establishes the project skeleton that all other tasks build on. After this task, `pip install -e ".[dev]"` works and the dev tools (ruff, mypy, pytest) are available.

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\pyproject.toml`
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\.gitignore`
3. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\.python-version`
4. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\README.md` (minimal — full version in Phase 7)

## Required Content (use VERBATIM)

### `.python-version`

```
3.11
```

### `README.md` (minimal)

```markdown
# HexRaysPyTools

Comprehensive toolkit for Hex-Rays decompiler.

See [docs/superpowers/specs/2026-06-18-hexrays-pytools-rewrite-design.md](docs/superpowers/specs/2026-06-18-hexrays-pytools-rewrite-design.md) for the rewrite design.
```

### `.gitignore`

```gitignore
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

### `pyproject.toml`

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

**NOTE:** A `README.md` is referenced in pyproject.toml. A minimal version is included in this task's file list; the full version will be created in Phase 7.

## Verification Steps (must pass)

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
pip install -e ".[dev]"
ruff --version
mypy --version
pytest --version
```

All four commands must succeed.

## Commit

```bash
git add pyproject.toml .gitignore .python-version README.md
git commit -m "chore: add project skeleton (pyproject.toml, .gitignore, .python-version, README.md)"
```

## Working Directory

`D:\re_dev_projects\ida-plugins\HexRaysPyTools`

## Report File

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-0.1-report.md`

## Report Contract

Write your full report to the report file with:
- What you created
- Verification command outputs (truncated if very long)
- Files created with line counts
- Self-review findings (if any)
- Any concerns

Then return to me with ONLY:
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commit SHA + subject
- One-line verification summary
- Report file path
