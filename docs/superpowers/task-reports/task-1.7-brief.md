# Task 1.7 Brief: Phase 1 gate verification

## Goal

Verify Phase 1 gate. The plugin can be imported and Session works, but IDA itself can't be tested in this env. Verify what's testable.

## Verification Commands

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools

# 1. Full test suite
PYTHONPATH=src pytest -v

# 2. Type check
python -m mypy --strict src/hexrays_pytools/

# 3. Lint
python -m ruff check src/hexrays_pytools/ tests/ tools/

# 4. Plugin entry import (with mock_ida preinstalled)
PYTHONPATH=src python -c "
import sys; sys.path.insert(0, 'tools')
import mock_ida; mock_ida.install()
from hexrays_pytools.__main__ import PLUGIN_ENTRY
print(PLUGIN_ENTRY)
"

# 5. Session roundtrip
PYTHONPATH=src python -c "
import sys; sys.path.insert(0, 'tools')
import mock_ida; mock_ida.install()
from hexrays_pytools.domain.session import Session
s = Session()
s.open()
s.imported_ea.add(0x1000)
s.close()
print(f'Session works: cached 0x{0x1000:x}')
"

# 6. List Phase 1 deliverables
ls -la src/hexrays_pytools/infra/arch/arch.py
ls -la src/hexrays_pytools/infra/idb/netnode.py
ls -la src/hexrays_pytools/domain/session.py
ls -la src/hexrays_pytools/domain/settings.py
ls -la src/hexrays_pytools/domain/recon/workspace.py
ls -la src/hexrays_pytools/plugin.py
ls -la src/hexrays_pytools/__main__.py
ls -la tools/hexrays_pytools_entry.py
```

## Expected Phase 1 Deliverables (8 new files)

1. `src/hexrays_pytools/infra/__init__.py` (empty)
2. `src/hexrays_pytools/infra/arch/__init__.py` (empty)
3. `src/hexrays_pytools/infra/arch/arch.py`
4. `src/hexrays_pytools/infra/idb/__init__.py` (empty)
5. `src/hexrays_pytools/infra/idb/netnode.py`
6. `src/hexrays_pytools/domain/__init__.py` (empty)
7. `src/hexrays_pytools/domain/session.py`
8. `src/hexrays_pytools/domain/settings.py`
9. `src/hexrays_pytools/domain/recon/__init__.py` (empty)
10. `src/hexrays_pytools/domain/recon/workspace.py`
11. `src/hexrays_pytools/plugin.py`
12. `src/hexrays_pytools/__main__.py`
13. `tools/hexrays_pytools_entry.py`

Plus updated mock_ida.py (from Task 1.1 and 1.6).

## Tag

If all gates pass:

```bash
git tag phase-1-infrastructure
git log --oneline -20
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-1.7-report.md`

DO NOT modify any files. Pure verification.

Status: DONE | DONE_WITH_CONCERNS | BLOCKED

If BLOCKED, report what failed. Otherwise report:
- All 4 test gates pass with concrete numbers (X/X tests, Y% coverage, mypy/ruff clean)
- All 13 deliverables exist
- Tag created
- Final coverage %
