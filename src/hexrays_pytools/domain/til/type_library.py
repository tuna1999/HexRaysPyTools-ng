"""Type library (TIL) operations.

Replaces `core/type_library.py`. The original used ctypes FFI to call
`enable_numbered_types` directly, with `linux2` (Py2-only) as a
fallback platform check. The rewrite uses `idaapi.enable_numbered_types`
if the IDA 9.x SDK exposes it; otherwise logs a warning and skips the
numbering (graceful degradation).
"""
from __future__ import annotations

import logging
from typing import Any

import idaapi  # type: ignore[import-not-found]
import idc  # type: ignore[import-not-found]

from ...ui.chooser import MyChoose

logger = logging.getLogger(__name__)


def choose_til() -> tuple[Any, ...] | None:
    """Prompt the user to pick a TIL from the loaded libraries.

    Returns (til_t, max_ordinal, is_local) or None if user cancels.
    """
    idati = idaapi.get_idati()
    libs = [(idati, idati.name, idati.desc)]
    for idx in range(idati.nbases):
        lib = idati.base(idx)
        libs.append((lib, lib.name, lib.desc))

    chooser = MyChoose(
        [[x[1], x[2]] for x in libs],
        "Select Library",
        [["Library", 10 | idaapi.Choose.CHCOL_PLAIN], ["Description", 30 | idaapi.Choose.CHCOL_PLAIN]],
        69,
    )
    pick = chooser.Show(True)
    if pick == -1:
        return None
    selected = libs[pick][0]
    max_ord = idaapi.get_ordinal_count(selected)
    if max_ord == idaapi.BADORD:
        # Try to enable numbered types via the official API; if missing, log and skip.
        enable = getattr(idaapi, "enable_numbered_types", None)
        if enable is None:
            logger.warning("idaapi.enable_numbered_types not available in this IDA version; skipping")
            return selected, 0, pick == 0
        enable(selected, True)
        max_ord = idaapi.get_ordinal_count(selected)
    return selected, int(max_ord), pick == 0


def create_type(name: str, declaration: str) -> bool:
    """Parse a C declaration and add it as a named type. Returns True on success."""
    tif = idaapi.tinfo_t()
    if tif.get_named_type(idaapi.get_idati(), name):
        logger.error("Type with name '%s' already exists", name)
        return False
    idaapi.idc_parse_types(declaration, 0)
    if not tif.get_named_type(idaapi.get_idati(), name):
        logger.error("Failed to create type '%s'", name)
        return False
    return True


def import_type(library: Any, name: str) -> int | None:
    """Import a named type from `library`. Returns new ordinal or None on failure."""
    last_ordinal = int(idaapi.get_ordinal_count(idaapi.get_idati()))
    type_id = idc.import_type(library, -1, name)
    if type_id == idaapi.BADORD:
        return None
    return last_ordinal
