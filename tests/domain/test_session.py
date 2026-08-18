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
    """Reopening refreshes IDA-derived caches instead of preserving stale values."""
    s = Session()
    s.idb_path = "/tmp/test.idb"
    s.open()
    s.imported_ea.add(0x1000)
    s.close()
    assert s.is_open is False
    s.open()
    assert 0x1000 not in s.imported_ea
    s.close()


def test_init_caches_populates_imports_and_demangled_names() -> None:
    import idaapi
    import idautils
    import idc

    idaapi.get_import_module_qty.return_value = 1

    def enum_imports(index, callback):  # type: ignore[no-untyped-def]
        assert index == 0
        callback(0x401000, "CreateFileW", 0)
        return True

    idaapi.enum_import_names.side_effect = enum_imports
    idautils.Names.return_value = [(0x402000, "?Method@Thing@@QEAAHXZ")]
    idc.demangle_name.return_value = "Thing::Method()"

    s = Session()
    s._init_caches()

    assert s.imported_ea == {0x401000}
    assert s.demangled_names["Thing_Method"] == {0x402000}
    assert s.touched_functions == set()


def test_session_open_initializes_recon_workspace() -> None:
    """open() creates a real ReconWorkspace (mirrors the original init()'s
    `cache.temporary_structure = TemporaryStructureModel()`).

    Without this, scanner actions see ``self._session.recon is None``
    and short-circuit with "no active session" warnings.
    """
    s = Session()
    s.open()
    assert s.recon is not None
    # The ReconWorkspace pre-creates its own StructureModel.
    assert s.recon.model is not None
    assert s.recon.model.rowCount() == 0
    assert s.recon.main_offset == 0


def test_session_open_initializes_xref_storage() -> None:
    """open() creates a real XrefStorage (mirrors the original ``XrefStorage().open()``)."""
    s = Session()
    s.open()
    assert s.xrefs is not None
