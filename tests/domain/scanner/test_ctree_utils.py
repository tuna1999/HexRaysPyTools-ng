"""Test ctree_utils."""
from unittest.mock import MagicMock

import idaapi  # type: ignore[import-not-found]

from hexrays_pytools.domain.scanner.ctree_utils import find_asm_address


def test_find_asm_address_returns_address_when_present() -> None:
    """find_asm_address returns the address when cexpr.ea is not BADADDR."""
    cexpr = MagicMock()
    cexpr.ea = 0x401000
    assert find_asm_address(cexpr) == 0x401000


def test_find_asm_address_returns_badaddr_when_badaddr() -> None:
    """find_asm_address returns BADADDR when cexpr.ea is BADADDR."""
    cexpr = MagicMock()
    cexpr.ea = idaapi.BADADDR
    assert find_asm_address(cexpr) == idaapi.BADADDR
