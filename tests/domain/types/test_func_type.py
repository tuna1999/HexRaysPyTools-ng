"""Test func_type."""
from unittest.mock import (
    MagicMock,
)

from hexrays_pytools.domain.types.func_type import (
    get_func_argument_info,
    set_func_argument,
    set_func_return,
)


def test_get_func_argument_info_returns_name_and_type() -> None:
    """get_func_argument_info returns (name, type) for valid arg_index."""
    idaapi = __import__("idaapi")
    func_tinfo = MagicMock()
    arg = MagicMock()
    arg.name = "size"
    arg.type = MagicMock()
    func_data = MagicMock()
    func_data.__len__.return_value = 2
    func_data.__getitem__.return_value = arg
    func_tinfo.get_func_details.return_value = True
    idaapi.func_type_data_t.return_value = func_data

    name, arg_type = get_func_argument_info(func_tinfo, 0)
    assert name == "size"


def test_set_func_argument_modifies_type() -> None:
    """set_func_argument changes the type of the argument at arg_index."""
    idaapi = __import__("idaapi")
    func_tinfo = MagicMock()
    func_data = MagicMock()
    func_data.__len__.return_value = 1
    func_data.__getitem__.return_value = MagicMock()
    func_tinfo.get_func_details.return_value = True
    func_tinfo.create_func.return_value = True
    idaapi.func_type_data_t.return_value = func_data

    new_type = MagicMock()
    assert set_func_argument(func_tinfo, 0, new_type) is True
    func_tinfo.create_func.assert_called_once()


def test_set_func_return_modifies_rettype() -> None:
    """set_func_return changes the return type."""
    idaapi = __import__("idaapi")
    func_tinfo = MagicMock()
    func_data = MagicMock()
    func_tinfo.get_func_details.return_value = True
    func_tinfo.create_func.return_value = True
    idaapi.func_type_data_t.return_value = func_data

    new_type = MagicMock()
    assert set_func_return(func_tinfo, new_type) is True
    assert func_data.rettype is new_type
