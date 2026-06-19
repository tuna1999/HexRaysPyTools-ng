# Task 1.3 Brief: domain/session.py

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\__init__.py` (empty)
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\session.py`
3. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\__init__.py` (empty)
4. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\test_session.py`

## Required Content (verbatim)

### `src/hexrays_pytools/domain/session.py`

```python
"""Per-IDB Session context.

Replaces all module-level global mutable state from the original plugin
(`cache.py`, `variable_scanner.py`, `classes.py`, `temporary_structure.py`).

Lifecycle: `MyPlugin.init()` calls `session.open()`;
`MyPlugin.term()` calls `session.close()`.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .recon.workspace import ReconWorkspace
    from .xrefs.xref_storage import XrefStorage
    from .templated.templated_types import TemplatedTypes

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Per-IDB state container. Created once per IDA database open."""

    is_open: bool = False
    idb_path: str = ""

    # Domain workspaces (lazy-init in open())
    recon: ReconWorkspace | None = None
    xrefs: XrefStorage | None = None
    templated: TemplatedTypes | None = None

    # IDA caches (replaces cache.py globals)
    imported_ea: set[int] = field(default_factory=set)
    demangled_names: dict[str, set[int]] = field(default_factory=dict)
    touched_functions: set[int] = field(default_factory=set)

    # Settings (loaded from HCLI ida-settings in open())
    log_level: int = logging.INFO
    propagate_through_all_names: bool = False
    store_xrefs: bool = True
    scan_any_type: bool = False
    templated_types_file: str = ""

    def open(self) -> None:
        """Open the session. Idempotent."""
        if self.is_open:
            return
        self._load_settings()
        self._init_caches()
        self._init_workspaces()
        self.is_open = True
        logger.info("Session opened for %s", self.idb_path or "<no IDB>")

    def close(self) -> None:
        """Close the session, persisting state. Idempotent."""
        if not self.is_open:
            return
        if self.xrefs and self.store_xrefs:
            self.xrefs.flush()
        self.is_open = False
        logger.info("Session closed")

    def _load_settings(self) -> None:
        """Load settings from HCLI ida-settings into session fields."""
        # settings.py is created in Task 1.4; fall back to defaults here
        try:
            from .settings import load_into
            load_into(self)
        except ImportError:
            logger.debug("settings.py not yet available, using defaults")

    def _init_caches(self) -> None:
        """Initialize IDA-derived caches (imported EAs, demangled names)."""
        # Imported EAs and demangled names are populated in later phases;
        # for now, just log.
        logger.debug("Caches initialized (stubs)")

    def _init_workspaces(self) -> None:
        """Lazy-init domain workspaces."""
        # Real init happens in Phase 2 (recon, xrefs, templated modules)
        # For now, just mark the slots.
        self.recon = None  # type: ignore[assignment]
        self.xrefs = None  # type: ignore[assignment]
        self.templated = None  # type: ignore[assignment]
```

### `tests/domain/test_session.py`

```python
"""Test Session lifecycle."""
from hexrays_pytools.domain.session import Session


def test_session_starts_closed() -> None:
    """A new Session has is_open=False."""
    s = Session()
    assert s.is_open is False


def test_session_open_sets_is_open() -> None:
    """open() sets is_open=True (idempotent)."""
    s = Session()
    s.open()
    assert s.is_open is True


def test_session_open_idempotent() -> None:
    """Calling open() twice doesn't error."""
    s = Session()
    s.open()
    s.open()  # should not raise
    assert s.is_open is True


def test_session_close_when_not_open() -> None:
    """close() on an unopened session doesn't error."""
    s = Session()
    s.close()  # should not raise
    assert s.is_open is False


def test_session_close_after_open() -> None:
    """close() sets is_open=False after open()."""
    s = Session()
    s.open()
    s.close()
    assert s.is_open is False


def test_session_default_settings() -> None:
    """Session has sane default values for all settings."""
    s = Session()
    assert s.log_level == 20  # logging.INFO
    assert s.propagate_through_all_names is False
    assert s.store_xrefs is True
    assert s.scan_any_type is False
    assert s.templated_types_file == ""


def test_session_default_caches_are_empty() -> None:
    """Session caches start as empty collections (not shared across instances)."""
    s1 = Session()
    s2 = Session()
    s1.imported_ea.add(0x1000)
    assert 0x1000 not in s2.imported_ea


def test_session_round_trip() -> None:
    """Session can be opened, mutated, closed, reopened."""
    s = Session()
    s.idb_path = "/tmp/test.idb"
    s.open()
    s.imported_ea.add(0x1000)
    s.close()
    assert s.is_open is False
    s.open()
    # Caches persist across open()/close() (they're not reset)
    assert 0x1000 in s.imported_ea
    s.close()
```

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/test_session.py -v
python -m mypy --strict src/hexrays_pytools/domain/session.py
python -m ruff check src/hexrays_pytools/domain/session.py tests/domain/
```

## Commit

```bash
git add src/hexrays_pytools/domain/session.py tests/domain/test_session.py src/hexrays_pytools/domain/__init__.py tests/domain/__init__.py
git commit -m "feat(domain): add Session dataclass (replaces global state)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-1.3-report.md`

Apply minimal lint fixes as needed. Document any deviations in DONE_WITH_CONCERNS.