"""Test func_type."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.types.func_type import (
    get_call_argument_info,
    get_func_arg_name,
    get_func_argument_info,
    set_func_arg_name,
    set_func_argument,
    set_func_return,
    set_funcptr_argument,
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


def test_get_func_argument_info_empty_when_get_func_details_fails() -> None:
    """get_func_argument_info returns ("", empty) when get_func_details fails."""
    idaapi = __import__("idaapi")
    func_tinfo = MagicMock()
    func_tinfo.get_func_details.return_value = False
    idaapi.func_type_data_t.return_value = MagicMock()
    name, arg_type = get_func_argument_info(func_tinfo, 0)
    assert name == ""


def test_get_func_argument_info_empty_when_index_out_of_range() -> None:
    """get_func_argument_info returns ("", empty) when arg_index >= nargs."""
    idaapi = __import__("idaapi")
    func_tinfo = MagicMock()
    func_data = MagicMock()
    func_data.__len__.return_value = 1
    func_tinfo.get_func_details.return_value = True
    idaapi.func_type_data_t.return_value = func_data
    name, arg_type = get_func_argument_info(func_tinfo, 5)
    assert name == ""


def test_set_func_argument_fails_when_get_func_details_fails() -> None:
    """set_func_argument returns False when get_func_details fails."""
    idaapi = __import__("idaapi")
    func_tinfo = MagicMock()
    func_tinfo.get_func_details.return_value = False
    idaapi.func_type_data_t.return_value = MagicMock()
    assert set_func_argument(func_tinfo, 0, MagicMock()) is False


def test_set_func_argument_fails_when_index_out_of_range() -> None:
    """set_func_argument returns False when arg_index >= nargs."""
    idaapi = __import__("idaapi")
    func_tinfo = MagicMock()
    func_data = MagicMock()
    func_data.__len__.return_value = 1
    func_tinfo.get_func_details.return_value = True
    idaapi.func_type_data_t.return_value = func_data
    assert set_func_argument(func_tinfo, 5, MagicMock()) is False


def test_set_func_return_fails_when_get_func_details_fails() -> None:
    """set_func_return returns False when get_func_details fails."""
    idaapi = __import__("idaapi")
    func_tinfo = MagicMock()
    func_tinfo.get_func_details.return_value = False
    idaapi.func_type_data_t.return_value = MagicMock()
    assert set_func_return(func_tinfo, MagicMock()) is False


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


def test_get_call_argument_info_finds_matching_arg() -> None:
    """get_call_argument_info returns (index, param_type) for the matching arg."""
    call_expr = MagicMock()
    arg0 = MagicMock()
    arg1 = MagicMock()
    target = MagicMock()
    call_expr.a = [arg0, target, arg1]
    func_tinfo = MagicMock()
    func_tinfo.get_nargs.return_value = 3
    param = MagicMock()
    func_tinfo.get_nth_arg.return_value = param
    call_expr.x.type.get_pointed_object.return_value = func_tinfo

    idx, p = get_call_argument_info(call_expr, target)
    assert idx == 1
    assert p is param


def test_get_call_argument_info_no_match() -> None:
    """get_call_argument_info returns (-1, None) when child is not an arg."""
    call_expr = MagicMock()
    call_expr.a = [MagicMock(), MagicMock()]
    idx, p = get_call_argument_info(call_expr, MagicMock())
    assert idx == -1
    assert p is None


def test_get_call_argument_info_param_none_when_index_exceeds_nargs() -> None:
    """get_call_argument_info returns param None when index >= nargs."""
    call_expr = MagicMock()
    target = MagicMock()
    call_expr.a = [target]
    func_tinfo = MagicMock()
    func_tinfo.get_nargs.return_value = 0  # no declared args
    call_expr.x.type.get_pointed_object.return_value = func_tinfo

    idx, p = get_call_argument_info(call_expr, target)
    assert idx == 0
    assert p is None


def test_set_funcptr_argument_rewraps_pointer() -> None:
    """set_funcptr_argument unwraps the ptr, sets arg, re-wraps."""
    funcptr = MagicMock()
    func_tinfo = MagicMock()
    funcptr.get_pointed_object.return_value = func_tinfo
    func_data = MagicMock()
    func_data.__len__.return_value = 1
    func_data.__getitem__.return_value = MagicMock()
    func_tinfo.get_func_details.return_value = True
    func_tinfo.create_func.return_value = True
    funcptr.create_ptr.return_value = True
    idaapi = __import__("idaapi")
    idaapi.func_type_data_t.return_value = func_data

    assert set_funcptr_argument(funcptr, 0, MagicMock()) is True
    funcptr.create_ptr.assert_called_once_with(func_tinfo)


def test_set_funcptr_argument_fails_when_inner_set_fails() -> None:
    """set_funcptr_argument returns False when the underlying set_func_argument fails."""
    funcptr = MagicMock()
    func_tinfo = MagicMock()
    funcptr.get_pointed_object.return_value = func_tinfo
    func_tinfo.get_func_details.return_value = False
    idaapi = __import__("idaapi")
    idaapi.func_type_data_t.return_value = MagicMock()

    assert set_funcptr_argument(funcptr, 0, MagicMock()) is False
    funcptr.create_ptr.assert_not_called()


def test_get_func_arg_name_returns_name() -> None:
    """get_func_arg_name returns the arg name when index is in range."""
    idaapi = __import__("idaapi")
    func_tinfo = MagicMock()
    func_tinfo.get_nargs.return_value = 2
    arg = MagicMock()
    arg.name = "size"
    func_data = MagicMock()
    func_data.__getitem__.return_value = arg
    idaapi.func_type_data_t.return_value = func_data
    assert get_func_arg_name(func_tinfo, 0) == "size"


def test_get_func_arg_name_none_when_out_of_range() -> None:
    """get_func_arg_name returns None when index >= nargs."""
    idaapi = __import__("idaapi")
    func_tinfo = MagicMock()
    func_tinfo.get_nargs.return_value = 1
    idaapi.func_type_data_t.return_value = MagicMock()
    assert get_func_arg_name(func_tinfo, 5) is None


def test_set_func_arg_name_sets_and_rebuilds() -> None:
    """set_func_arg_name sets the arg name and rebuilds the func type."""
    idaapi = __import__("idaapi")
    func_tinfo = MagicMock()
    arg = MagicMock()
    func_data = MagicMock()
    func_data.__getitem__.return_value = arg
    idaapi.func_type_data_t.return_value = func_data
    set_func_arg_name(func_tinfo, 1, "count")
    assert arg.name == "count"
    func_tinfo.create_func.assert_called_once_with(func_data)

