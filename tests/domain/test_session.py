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
