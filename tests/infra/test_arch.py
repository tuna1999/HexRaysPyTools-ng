"""Test arch.is_code_ea and arch.get_ptr."""
from hexrays_pytools.infra.arch.arch import (
    get_funcs_calling_address,
    get_ptr,
    is_code_ea,
    to_hex,
)


def test_is_code_ea_strips_arm_thumb_bit() -> None:
    """is_code_ea(0x1001) should mask off the thumb bit before checking."""
    is_code_ea(0x1001)
    idaapi = __import__("idaapi")
    # The mock records the call to get_full_flags with the masked address
    call_args = idaapi.get_full_flags.call_args
    assert call_args[0][0] == 0x1000  # 0x1001 & ~1


def test_is_code_ea_returns_bool() -> None:
    """is_code_ea returns the result of idaapi.is_code()."""
    __import__("idaapi").is_code.return_value = True
    assert is_code_ea(0x1000) is True


def test_get_ptr_x86_uses_wide_dword() -> None:
    """get_ptr on 32-bit IDA reads a wide dword."""
    __import__("idaapi").get_64bit.return_value = False
    get_ptr(0x2000)
    __import__("idaapi").get_wide_dword.assert_called()


def test_get_ptr_x64_uses_qword() -> None:
    """get_ptr on 64-bit IDA reads a qword for data, dword for code."""
    idaapi = __import__("idaapi")
    idaapi.get_64bit.return_value = True
    idaapi.is_data.return_value = True
    get_ptr(0x2000)
    idaapi.get_qword.assert_called()


def test_to_hex_64bit() -> None:
    """to_hex formats as 16-digit hex on 64-bit IDA."""
    __import__("idaapi").get_64bit.return_value = True
    assert to_hex(0xDEADBEEF) == "0x00000000DEADBEEF"


def test_to_hex_32bit() -> None:
    """to_hex formats as 8-digit hex on 32-bit IDA."""
    __import__("idaapi").get_64bit.return_value = False
    assert to_hex(0xDEADBEEF) == "0xDEADBEEF"


def test_get_funcs_calling_address_collects_callers() -> None:
    """get_funcs_calling_address walks code xrefs to the target."""
    idaapi = __import__("idaapi")
    idc = __import__("idc")
    # Simulate two crefs to 0x5000, then BADADDR to stop the loop.
    idaapi.get_first_cref_to.return_value = 0x1000
    idaapi.get_next_cref_to.side_effect = [0x2000, idaapi.BADADDR]
    idc.get_func_attr.side_effect = lambda ea, attr: ea  # func start == xref ea
    result = get_funcs_calling_address(0x5000)
    assert result == {0x1000, 0x2000}


def test_get_funcs_calling_address_skips_badaddr_funcs() -> None:
    """get_funcs_calling_address skips xrefs whose function is BADADDR."""
    idaapi = __import__("idaapi")
    idc = __import__("idc")
    idaapi.get_first_cref_to.return_value = 0x1000
    idaapi.get_next_cref_to.return_value = idaapi.BADADDR
    idc.get_func_attr.return_value = idaapi.BADADDR  # no containing function
    assert get_funcs_calling_address(0x5000) == set()
