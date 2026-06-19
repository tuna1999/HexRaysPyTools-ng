# Task 0.2 Brief: Package Skeleton

## Where This Fits

Task 0.1 created the project skeleton. This task creates the `hexrays_pytools` Python package directory with a version-exposing `__init__.py`. All subsequent tasks create files inside this package.

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\__init__.py`

## Required Content (use VERBATIM)

```python
"""HexRaysPyTools — comprehensive toolkit for Hex-Rays decompiler."""

__version__ = "2.0.0"

__all__ = ["__version__"]
```

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
python -c "import hexrays_pytools; print(hexrays_pytools.__version__)"
```

Expected output: `2.0.0`

## Commit

```bash
git add src/hexrays_pytools/__init__.py
git commit -m "chore: create hexrays_pytools package skeleton"
```

## Working Directory

`D:\re_dev_projects\ida-plugins\HexRaysPyTools`

## Report File

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-0.2-report.md`

## Report Contract

Write your full report to the report file. Return status + commit SHA + 1-line summary + report path.
