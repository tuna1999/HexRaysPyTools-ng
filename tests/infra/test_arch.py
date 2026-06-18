"""Test arch.is_code_ea and arch.get_ptr."""
from hexrays_pytools.infra.arch.arch import get_ptr, is_code_ea


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
