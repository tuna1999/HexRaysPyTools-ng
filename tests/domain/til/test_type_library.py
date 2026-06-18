"""Test type_library."""
from unittest.mock import MagicMock, patch

from hexrays_pytools.domain.til.type_library import (
    choose_til,
    create_type,
    import_type,
)


def test_create_type_succeeds_for_new_type() -> None:
    """create_type returns True for a new type name."""
    idaapi = __import__("idaapi")
    tif = MagicMock()
    idaapi.tinfo_t.return_value = tif
    # First call (existence check) returns False (not exists)
    # Second call (verify) returns True
    tif.get_named_type.side_effect = [False, True]
    assert create_type("MyStruct", "struct MyStruct { int x; };") is True


def test_create_type_fails_if_already_exists() -> None:
    """create_type returns False if name already exists."""
    idaapi = __import__("idaapi")
    tif = MagicMock()
    idaapi.tinfo_t.return_value = tif
    tif.get_named_type.return_value = True  # name already exists
    assert create_type("Existing", "struct Existing { int x; };") is False


def test_import_type_returns_ordinal_on_success() -> None:
    """import_type returns the new ordinal on success."""
    idaapi = __import__("idaapi")
    idc = __import__("idc")
    idaapi.get_ordinal_count.return_value = 42
    idc.import_type.return_value = 5  # not BADORD
    assert import_type(MagicMock(), "MyType") == 42


def test_import_type_returns_none_on_failure() -> None:
    """import_type returns None if idc.import_type returns BADORD."""
    idaapi = __import__("idaapi")
    idc = __import__("idc")
    idaapi.BADORD = -1
    idc.import_type.return_value = -1
    assert import_type(MagicMock(), "MissingType") is None


def test_choose_til_returns_none_on_cancel() -> None:
    """choose_til returns None when user cancels the chooser."""
    # Patch MyChoose in the namespace where choose_til looks it up.
    # type_library binds the name via `from ...ui.chooser import MyChoose`,
    # so the patch must target type_library's namespace (not ui.chooser's) to
    # take effect — see unittest.mock docs on "where to patch".
    import hexrays_pytools.domain.til.type_library as tl_mod

    with patch.object(tl_mod, "MyChoose") as mock_choose:
        instance = MagicMock()
        instance.Show.return_value = -1
        mock_choose.return_value = instance
        assert choose_til() is None


def test_create_type_returns_false_when_idc_parse_types_fails() -> None:
    """create_type returns False when type creation fails (verify re-check)."""
    idaapi = __import__("idaapi")
    tif = MagicMock()
    tif.get_named_type.return_value = False  # both calls return False
    idaapi.tinfo_t.return_value = tif
    assert create_type("NewType", "struct NewType { int x; };") is False


def test_choose_til_returns_tuple_on_success() -> None:
    """choose_til returns (til, max_ord, is_local) on a normal pick."""
    import hexrays_pytools.domain.til.type_library as tl_mod

    idaapi = __import__("idaapi")
    idati = MagicMock()
    idati.name = "idati"
    idati.desc = "Main TIL"
    idati.nbases = 0
    idaapi.get_idati.return_value = idati
    idaapi.get_ordinal_count.return_value = 10  # not BADORD
    with patch.object(tl_mod, "MyChoose") as mock_choose:
        instance = MagicMock()
        instance.Show.return_value = 0  # first library
        mock_choose.return_value = instance
        result = choose_til()
    assert result is not None
    til, max_ord, is_local = result
    assert til is idati
    assert max_ord == 10
    assert is_local is True


def test_choose_til_falls_back_when_badord_and_no_enable() -> None:
    """choose_til returns max_ord=0 when get_ordinal_count==BADORD and enable is unavailable.

    The production fallback uses ``getattr(idaapi, "enable_numbered_types", None)``.
    Under the test ``_MockIdaModule``, unknown attributes resolve to MagicMocks, so to
    exercise the ``enable is None`` branch we swap the idaapi global inside type_library
    for a MagicMock that raises ``AttributeError`` specifically for that one name (so
    ``getattr(..., None)`` yields None), then restore it.
    """
    import hexrays_pytools.domain.til.type_library as tl_mod

    idati = MagicMock()
    idati.name = "idati"
    idati.desc = "Main TIL"
    idati.nbases = 0

    class _NoEnableMock(MagicMock):
        """MagicMock that genuinely lacks ``enable_numbered_types``."""

        def __getattr__(self, name: str) -> object:
            if name == "enable_numbered_types":
                raise AttributeError(name)
            return super().__getattr__(name)

    fake = _NoEnableMock()
    fake.BADORD = 0xFFFFFFFFFFFFFFFF
    fake.get_idati.return_value = idati
    fake.get_ordinal_count.return_value = fake.BADORD

    saved = tl_mod.idaapi
    tl_mod.idaapi = fake  # type: ignore[assignment]
    try:
        with patch.object(tl_mod, "MyChoose") as mock_choose:
            instance = MagicMock()
            instance.Show.return_value = 0
            mock_choose.return_value = instance
            result = tl_mod.choose_til()
    finally:
        tl_mod.idaapi = saved  # type: ignore[assignment]
    assert result is not None
    _til, max_ord, _is_local = result
    assert max_ord == 0


def test_choose_til_calls_enable_numbered_types_when_available() -> None:
    """choose_til re-queries ordinal count after enable_numbered_types."""
    import hexrays_pytools.domain.til.type_library as tl_mod

    idaapi = __import__("idaapi")
    idati = MagicMock()
    idati.name = "idati"
    idati.desc = "Main TIL"
    idati.nbases = 0
    idaapi.get_idati.return_value = idati
    # First call (BADORD), second call after enable (128)
    idaapi.get_ordinal_count.side_effect = [idaapi.BADORD, 128]
    enable = MagicMock()
    idaapi.enable_numbered_types = enable
    try:
        with patch.object(tl_mod, "MyChoose") as mock_choose:
            instance = MagicMock()
            instance.Show.return_value = 0
            mock_choose.return_value = instance
            result = choose_til()
    finally:
        del idaapi.enable_numbered_types
    assert result is not None
    _til, max_ord, _is_local = result
    assert max_ord == 128
    enable.assert_called_once_with(idati, True)


def test_choose_til_with_extra_bases() -> None:
    """choose_til enumerates extra library bases from idati."""
    import hexrays_pytools.domain.til.type_library as tl_mod

    idaapi = __import__("idaapi")
    idati = MagicMock()
    idati.name = "idati"
    idati.desc = "Main TIL"
    idati.nbases = 2
    base0 = MagicMock()
    base0.name = "extra0"
    base0.desc = "Extra 0"
    base1 = MagicMock()
    base1.name = "extra1"
    base1.desc = "Extra 1"
    idati.base.side_effect = [base0, base1]
    idaapi.get_idati.return_value = idati
    idaapi.get_ordinal_count.return_value = 5
    with patch.object(tl_mod, "MyChoose") as mock_choose:
        instance = MagicMock()
        instance.Show.return_value = 1  # pick first extra base
        mock_choose.return_value = instance
        result = choose_til()
    assert result is not None
    til, _max_ord, is_local = result
    assert til is base0
    assert is_local is False  # not the first (idati)
