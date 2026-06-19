# Task 1.5 Brief: domain/recon/workspace.py

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\recon\__init__.py` (empty)
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\recon\workspace.py`
3. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\recon\__init__.py` (empty)
4. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\recon\test_workspace.py`

## Required Content (verbatim)

### `src/hexrays_pytools/domain/recon/workspace.py`

```python
"""ReconWorkspace — container for the structure reconstruction model.

Replaces `cache.temporary_structure` global from the original plugin.
Phase 2 will expand this with the actual `StructureModel` (QAbstractTableModel);
for Phase 1 we just establish the skeleton so Session.recon can point to it.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


class ReconWorkspace:
    """Workspace for the structure reconstruction feature.

    Holds the temporary structure model being built (Phase 2 adds the Qt model).
    One instance per Session.
    """

    def __init__(self) -> None:
        self._model: object | None = None  # StructureModel added in Phase 2

    @property
    def model(self) -> object | None:
        """The current structure model (None until Phase 2 wires it)."""
        return self._model

    def clear(self) -> None:
        """Clear all workspace state."""
        self._model = None
        logger.debug("ReconWorkspace cleared")

    def is_empty(self) -> bool:
        """Return True if the workspace has no active model."""
        return self._model is None
```

### `tests/domain/recon/test_workspace.py`

```python
"""Test ReconWorkspace skeleton."""
from hexrays_pytools.domain.recon.workspace import ReconWorkspace


def test_workspace_starts_empty() -> None:
    """A new ReconWorkspace has no model."""
    w = ReconWorkspace()
    assert w.is_empty() is True
    assert w.model is None


def test_workspace_clear_keeps_empty() -> None:
    """clear() on an empty workspace is a no-op."""
    w = ReconWorkspace()
    w.clear()
    assert w.is_empty() is True


def test_workspace_instances_are_independent() -> None:
    """Two ReconWorkspaces don't share state."""
    w1 = ReconWorkspace()
    w2 = ReconWorkspace()
    # Mock setting model on w1 should not affect w2
    w1._model = "fake"  # type: ignore[assignment]
    assert w2.is_empty() is True


def test_workspace_can_hold_a_model() -> None:
    """After setting model, is_empty() returns False."""
    w = ReconWorkspace()
    w._model = object()
    assert w.is_empty() is False
    assert w.model is not None


def test_workspace_clear_after_model() -> None:
    """clear() removes the model reference."""
    w = ReconWorkspace()
    w._model = object()
    w.clear()
    assert w.is_empty() is True
    assert w.model is None
```

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/recon/test_workspace.py -v
python -m mypy --strict src/hexrays_pytools/domain/recon/workspace.py
python -m ruff check src/hexrays_pytools/domain/recon/ tests/domain/recon/
```

## Commit

```bash
git add src/hexrays_pytools/domain/recon/ tests/domain/recon/
git commit -m "feat(domain): add ReconWorkspace skeleton (replaces cache.temporary_structure)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-1.5-report.md`

Apply minimal lint fixes as needed. Document any deviations in DONE_WITH_CONCERNS.