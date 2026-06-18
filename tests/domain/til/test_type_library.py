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
