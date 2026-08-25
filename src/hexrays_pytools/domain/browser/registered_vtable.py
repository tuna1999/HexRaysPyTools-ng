"""Registered (browser) VirtualMethod + RegisteredVTable.

Ported from ``refs/HexRaysPyTools/HexRaysPyTools/core/classes.py:18-167``
(:class:`VirtualMethod`) and :class:`VirtualTable` (lines 169-284).

The dataclass form (``@dataclass``) is preserved for snapshot semantics, but
all the rich behaviour (data/setData/font/flags/color, name demangling,
tinfo derivation via decompile, set_first_argument_type, open_function,
commit, __eq__, __repr__) is ported as plain methods / properties so the
:class:`TreeModel` can drive the user-visible editing round-trip.

The :class:`VirtualTable` reads/writes ``all_virtual_tables`` registry via
:class:`Class.create_class` flow; we don't keep module globals (those
existed purely for cross-window deduplication which Session-scoped caches
now cover).
"""

from __future__ import annotations

# ruff: noqa: N802, N806, SIM102, SIM105
import contextlib
import logging
from dataclasses import dataclass, field
from typing import Any

import idaapi  # type: ignore[import-not-found]
import idc  # type: ignore[import-not-found]

from ...infra.arch.arch import to_hex

logger = logging.getLogger(__name__)


@dataclass
class VirtualMethod:
    """A virtual method entry inside a :class:`RegisteredVTable`.

    Mirrors the original ``VirtualMethod`` class line-by-line: editable
    name + signature, ``ra_addresses`` resolution, edit-state tracking
    (``name_modified`` / ``tinfo_modified``), parent tracking for
    cascade-update of the ``modified`` flag up the tree, font flags for
    italicising modified entries.
    """

    name: str
    tinfo: Any = None
    address: int = 0
    parent: Any = None  # RegisteredVTable (forward ref)
    tinfo_modified: bool = False
    name_modified: bool = False
    class_name: str | None = None
    parents: list[Any] = field(default_factory=list)
    ra_addresses: list[int] = field(default_factory=list)
    rowcount: int = 0
    children: list[Any] = field(default_factory=list)
    offset: int = 0  # byte offset within the vtable (browser test compat)

    def __post_init__(self) -> None:
        # If a parent was passed in the constructor, register it.
        if self.parent is not None and self.parent not in self.parents:
            self.parents.append(self.parent)
        if self.name and not self.ra_addresses:
            image_base = int(idaapi.get_imagebase())
            addresses: set[int] = set()
            try:
                direct = int(idc.get_name_ea_simple(self.name))
                if direct != int(idaapi.BADADDR):
                    addresses.add(direct)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                pass
            self.ra_addresses = sorted(int(ea) - image_base for ea in addresses)

    def update(self, name: str, tinfo: Any) -> None:
        """Reset edit-state when the parent vtable pulls fresh data from local types."""
        self.name = name
        self.tinfo = tinfo
        self.name_modified = False
        self.tinfo_modified = False

    @property
    def addresses(self) -> list[int]:
        """Resolve ra_addresses back to absolute EAs."""
        image_base = int(idaapi.get_imagebase())
        return [int(ra) + image_base for ra in self.ra_addresses]

    def data(self, column: int) -> Any:  # noqa: N802 (Qt API)
        if column == 0:
            return self.name
        if column == 1:
            try:
                return self.tinfo.get_pointed_object().dstr()
            except (AttributeError, RuntimeError):
                return str(self.tinfo)
        if column == 2:
            addrs = self.addresses
            if len(addrs) > 1:
                return "LIST"
            if len(addrs) == 1:
                return to_hex(int(addrs[0]))
        return None

    def setData(self, column: int, value: str) -> bool:  # noqa: N802 (Qt API)
        """In-place edit. Returns True if accepted (mirrors original setData)."""
        if column == 0:
            if bool(idaapi.is_ident(str(value))) and self.name != value:
                self.name = str(value)
                self.name_modified = True
                for parent in self.parents:
                    parent.modified = True
                return True
        elif column == 1:
            tinfo = idaapi.tinfo_t()
            try:
                split = str(value).split("(")
            except Exception:  # noqa: BLE001
                return False
            if len(split) == 2:
                value2 = split[0] + " " + self.name + "(" + split[1] + ";"
                try:
                    if (  # noqa: SIM102
                        idaapi.parse_decl(tinfo, idaapi.get_idati(), value2, idaapi.PT_TYP)
                        is not None
                    ):
                        if tinfo.is_func():
                            tinfo.create_ptr(tinfo)
                            if tinfo.dstr() != self.tinfo.dstr():
                                self.tinfo = tinfo
                                self.tinfo_modified = True
                                for parent in self.parents:
                                    parent.modified = True
                                return True
                except (AttributeError, RuntimeError):
                    pass
        return False

    def font(self, column: int) -> Any:  # noqa: N802 (Qt API)
        from PySide6 import QtGui

        if column == 0 and self.name_modified:
            return QtGui.QFont("Consolas", 10, italic=True)
        if column == 1 and self.tinfo_modified:
            return QtGui.QFont("Consolas", 10, italic=True)
        return QtGui.QFont("Consolas", 10, 0)

    def flags(self, column: int) -> Any:  # noqa: N802 (Qt API)
        """Editable only if there's exactly one address."""
        from PySide6 import QtCore

        if column != 2 and len(self.addresses) == 1:
            return (
                QtCore.Qt.ItemFlag.ItemIsSelectable
                | QtCore.Qt.ItemFlag.ItemIsEnabled
                | QtCore.Qt.ItemFlag.ItemIsEditable
            )
        return QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled

    @property
    def color(self) -> Any:
        from PySide6 import QtGui

        return QtGui.QColor("#fefbd8")

    def tooltip(self) -> str:
        """Render a human-readable tooltip from name + parent + offset.

        Tests ``test_tooltip_with_tinfo`` requires ``"Foo_vtable" in v.tooltip()``
        and ``test_tooltip_without_tinfo`` requires ``"Foo" in hint``,
        ``"vtable" in hint``, ``"0x10" in hint``. Mirrors the original's
        ``name + class_name + offset`` rendering.

        Note: this is a **method** (callable as ``v.tooltip()``) — tests
        use parens, so a property returning a string would not match.
        """
        parts: list[str] = []
        if self.class_name:
            parts.append(str(self.class_name))
        if self.name:
            parts.append(str(self.name))
        if self.offset:
            parts.append(f"@0x{int(self.offset):X}")
        if self.tinfo is not None and hasattr(self.tinfo, "dstr"):
            try:
                parts.append(str(self.tinfo.dstr()))
            except Exception:  # noqa: BLE001
                pass
        return " ".join(parts) if parts else ""

    def set_first_argument_type(self, name: str) -> None:
        """Set `this` pointer as first arg. Mirrors original lines 113-133."""
        from ..types.tinfo_utils import is_legal_type

        func_data = idaapi.func_type_data_t()
        try:
            func_tinfo = self.tinfo.get_pointed_object()
        except (AttributeError, RuntimeError):
            return
        class_tinfo = idaapi.tinfo_t()
        try:
            if not (
                func_tinfo.get_func_details(func_data)
                and func_tinfo.get_nargs()
                and class_tinfo.get_named_type(idaapi.get_idati(), name)
            ):
                return
        except (AttributeError, RuntimeError):
            return
        class_tinfo.create_ptr(class_tinfo)
        try:
            first_arg_tinfo = func_data[0].type
        except (IndexError, AttributeError):
            return
        if (
            first_arg_tinfo.is_ptr()
            and first_arg_tinfo.get_pointed_object().is_udt()
        ) or is_legal_type(first_arg_tinfo):
            try:
                func_data[0].type = class_tinfo
                func_data[0].name = "this"
                func_tinfo.create_func(func_data)
                func_tinfo.create_ptr(func_tinfo)
                if func_tinfo.dstr() != self.tinfo.dstr():
                    self.tinfo = func_tinfo
                    self.tinfo_modified = True
                    for parent in self.parents:
                        parent.modified = True
            except (AttributeError, RuntimeError):
                pass
        else:
            logger.warning(
                "function %s probably has wrong type — skipping set_first_argument_type",
                self.name,
            )

    def open_function(self) -> None:
        """Open the (decompiled) pseudocode window for the first matching address."""
        from ...domain.scanner.helpers import decompile_function

        addrs = self.addresses
        if len(addrs) > 1:
            from ...infra.arch.arch import choose_virtual_func_address

            address = choose_virtual_func_address(self.name)
            if not address:
                return
        elif len(addrs) == 1:
            address = int(addrs[0])
        else:
            return

        cfunc = decompile_function(address)
        if cfunc:
            with contextlib.suppress(AttributeError, RuntimeError):
                idaapi.open_pseudocode(int(address), 0)
        else:
            with contextlib.suppress(AttributeError, RuntimeError):
                idaapi.jumpto(int(address))

    def commit(self) -> None:
        """Push ``name`` + ``tinfo`` back to IDA Local Types. Mirrors original L151-160."""
        addrs = self.addresses
        if self.name_modified:
            self.name_modified = False
            if len(addrs) == 1:
                with contextlib.suppress(AttributeError, RuntimeError):
                    idaapi.set_name(int(addrs[0]), self.name)
        if self.tinfo_modified:
            self.tinfo_modified = False
            if len(addrs) == 1:
                try:
                    pointed = self.tinfo.get_pointed_object()
                    idaapi.apply_tinfo(int(addrs[0]), pointed, idaapi.TINFO_DEFINITE)
                except (AttributeError, RuntimeError):
                    pass

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VirtualMethod):
            return NotImplemented
        return self.addresses == other.addresses

    def __repr__(self) -> str:
        return self.name


@dataclass
class RegisteredVTable:
    """A virtual table that lives in IDA Local Types.

    Mirrors the original ``VirtualTable`` class line-by-line: holds an
    ordinal and the virtual functions it points to; tracks a ``modified``
    flag that cascades to all parent classes; supports in-place rename of
    column 0; serialises the modified virtual functions back into a UDT
    on ``update_local_type``.
    """

    name: str
    ordinal: int = 0
    tinfo: Any = None
    class_: list[Any] = field(default_factory=list)  # Class parent(s)
    class_name: str | None = None
    offset: int = 0
    virtual_functions: list[VirtualMethod] = field(default_factory=list)
    _modified: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            try:
                self.name = str(self.tinfo.dstr())
            except (AttributeError, RuntimeError):
                self.name = ""

    def populate_virtual_functions(
        self,
        demangled_names: dict[str, set[int]] | None = None,
    ) -> None:
        """Populate browser entries from the current vtable UDT."""
        udt_data = idaapi.udt_type_data_t()
        try:
            if self.tinfo is None or not self.tinfo.get_udt_details(udt_data):
                return
        except (AttributeError, RuntimeError):
            return
        self.virtual_functions = []
        for member in udt_data:
            vf = VirtualMethod(
                name=str(member.name),
                tinfo=member.type,
                parent=self,
                class_name=self.class_name,
                offset=int(member.offset) // 8,
            )
            if demangled_names:
                image_base = int(idaapi.get_imagebase())
                candidates = demangled_names.get(vf.name, set())
                if not candidates and self.class_name:
                    candidates = demangled_names.get(f"{self.class_name}_{vf.name}", set())
                if candidates:
                    vf.ra_addresses = sorted(int(ea) - image_base for ea in candidates)
            self.virtual_functions.append(vf)

    def update(self) -> None:
        """Re-pull vtable members from IDA Local Types. Mirrors original L179-192."""
        if not self.modified:
            return
        try:
            vtable_tinfo = idaapi.tinfo_t()
            vtable_tinfo.get_numbered_type(idaapi.get_idati(), int(self.ordinal))
            udt_data = idaapi.udt_type_data_t()
            vtable_tinfo.get_udt_details(udt_data)
            self.tinfo = vtable_tinfo
            self.name = str(vtable_tinfo.dstr())
            self.modified = False
            if len(self.virtual_functions) == len(udt_data):
                for current_function, other_function in zip(
                    self.virtual_functions, udt_data, strict=False
                ):
                    current_function.update(str(other_function.name), other_function.type)
            else:
                logger.warning(
                    "[ERROR] Something have been modified in Local types — please refresh this view"
                )
        except (AttributeError, RuntimeError) as e:
            logger.warning("VTable.update failed: %s", e)

    def update_local_type(self) -> None:
        """Push edits back to the UDT. Mirrors original L194-208."""
        if not self.modified:
            return
        try:
            final_tinfo = idaapi.tinfo_t()
            udt_data = idaapi.udt_type_data_t()
            self.tinfo.get_udt_details(udt_data)
            if len(udt_data) == len(self.virtual_functions):
                for udt_member, virtual_function in zip(
                    udt_data, self.virtual_functions, strict=False
                ):
                    udt_member.name = virtual_function.name
                    udt_member.type = virtual_function.tinfo
                    virtual_function.commit()
                final_tinfo.create_udt(udt_data, idaapi.BTF_STRUCT)
                final_tinfo.set_numbered_type(
                    idaapi.get_idati(),
                    int(self.ordinal),
                    idaapi.NTF_REPLACE,
                    self.name,
                )
                self.modified = False
            else:
                logger.warning(
                    "[ERROR] Something have been modified in Local types — please refresh this view"
                )
        except (AttributeError, RuntimeError) as e:
            logger.warning("VTable.update_local_type failed: %s", e)

    def set_first_argument_type(self, class_name: str) -> None:
        """Apply `this` pointer to every virtual function. Mirrors original L210-212."""
        for function in self.virtual_functions:
            function.set_first_argument_type(class_name)

    @property
    def modified(self) -> bool:
        return self._modified

    @modified.setter
    def modified(self, value: bool) -> None:
        self._modified = bool(value)
        if value:
            for cls in self.class_:
                cls.modified = True

    def get_class_tinfo(self) -> Any:
        if len(self.class_) == 1:
            return self.class_[0].tinfo
        return None

    def setData(self, column: int, value: str) -> bool:  # noqa: N802 (Qt API)
        if column == 0 and bool(idaapi.is_ident(str(value))) and self.name != value:
            self.name = str(value)
            self.modified = True
            return True
        return False

    def data(self, column: int) -> Any:  # noqa: N802 (Qt API)
        if column == 0:
            return self.name
        return None

    @property
    def color(self) -> Any:
        from PySide6 import QtGui

        return QtGui.QColor("#d5f4e6")

    def tooltip(self) -> str:
        """Render a tooltip for the vtable (name + class_name + offset + tinfo).

        The :class:`TreeModel`'s :attr:`Qt.ItemDataRole.ToolTipRole` calls
        this method on every node, so we include all identifying
        information: parent class name, vtable name, offset, and the
        type's C declaration if available.
        """
        parts: list[str] = []
        if self.class_name:
            parts.append(str(self.class_name))
        if self.name:
            parts.append(str(self.name))
        if self.offset:
            parts.append(f"@0x{int(self.offset):X}")
        if self.tinfo is not None and hasattr(self.tinfo, "dstr"):
            try:
                parts.append(str(self.tinfo.dstr()))
            except Exception:  # noqa: BLE001
                pass
        return " ".join(parts) if parts else ""

    def font(self, column: int) -> Any:  # noqa: N802 (Qt API)
        from PySide6 import QtGui

        if self.modified:
            return QtGui.QFont("Consolas", 12, italic=True)
        return QtGui.QFont("Consolas", 12)

    def flags(self, column: int) -> Any:  # noqa: N802 (Qt API)
        from PySide6 import QtCore

        if column == 0:
            return (
                QtCore.Qt.ItemFlag.ItemIsSelectable
                | QtCore.Qt.ItemFlag.ItemIsEditable
                | QtCore.Qt.ItemFlag.ItemIsEnabled
            )
        return QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled

    @property
    def children(self) -> list[VirtualMethod]:
        return self.virtual_functions

    def __repr__(self) -> str:
        return str(self.virtual_functions)
