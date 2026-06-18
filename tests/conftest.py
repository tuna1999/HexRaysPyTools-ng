"""Pytest configuration: install mock IDA modules before any test runs.

This file is auto-loaded by pytest. We install mocks at the top level so that
tests can `import hexrays_pytools.*` without IDA being installed.
"""
import sys
from pathlib import Path
from typing import Any

# Add tools/ to sys.path so `import mock_ida` works
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

# Install mocks immediately on conftest load
import mock_ida  # type: ignore[import-not-found]  # noqa: E402

mock_ida.install()


def pytest_runtest_setup(item: Any) -> None:
    """Reset mock call history before each test for isolation."""
    mock_ida.reset()
