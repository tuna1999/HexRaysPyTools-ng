# Task 2.15 Brief: Phase 2 gate verification

## Goal

Verify Phase 2 gate. All 12 Phase 2 tasks done. Tag phase-2-core-domain.

## Verification Commands

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools

# 1. Full test suite (with coverage gate)
PYTHONPATH=src pytest -v

# 2. Type check
python -m mypy --strict src/hexrays_pytools/

# 3. Lint
python -m ruff check src/hexrays_pytools/ tests/ tools/

# 4. List Phase 2 deliverables
ls src/hexrays_pytools/domain/types/
ls src/hexrays_pytools/domain/scanner/
ls src/hexrays_pytools/domain/recon/
ls src/hexrays_pytools/domain/xrefs/
ls src/hexrays_pytools/domain/templated/
ls src/hexrays_pytools/domain/til/
ls src/hexrays_pytools/domain/graph/
```

## Expected Phase 2 Deliverables

### domain/types/
- `__init__.py`
- `tinfo_utils.py`
- `func_type.py`
- `udt_builder.py`

### domain/scanner/
- `__init__.py`
- `visitor_base.py`
- `scanned_object.py`
- `ctree_utils.py`
- `member_extractor.py`

### domain/recon/
- `__init__.py`
- `workspace.py` (updated in refactor commit)
- `member.py`
- `discovered_vtable.py`
- `structure_model.py`

### domain/xrefs/
- `__init__.py`
- `xref_storage.py`

### domain/templated/
- `__init__.py`
- `templated_types.py`
- `data/__init__.py`
- `data/templated_types.toml`

### domain/til/
- `__init__.py`
- `type_library.py`

### domain/graph/
- `__init__.py`
- `structure_graph.py`

## Tag

```bash
git tag phase-2-core-domain
git log --oneline -25
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.15-report.md`

DO NOT modify any files.

Status: DONE | DONE_WITH_CONCERNS | BLOCKED

If BLOCKED, report what failed. Otherwise report:
- All gates pass with concrete numbers
- All deliverables exist
- Tag created
- Final coverage %