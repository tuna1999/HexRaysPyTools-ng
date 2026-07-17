"""QAbstractTableModel for the Structure Builder widget.

Ported from ``refs/HexRaysPyTools/HexRaysPyTools/core/temporary_structure.py:TemporaryStructureModel``.

This is the working-copy model for the struct reconstruction feature. It
holds a list of :class:`AbstractMember` candidates the user is assembling,
emits Qt signals for the bound ``QTableView``, and exposes the operations
the Structure Builder buttons invoke (pack, finalize, disable/enable,
origin, array, pack/unpack substructure, remove, resolve, load, clear,
recognize-shape, set-stl-type).

End-to-end correctness requires Hex-Rays ctree / UDT APIs that the
``tools/mock_ida.py`` mock does not reproduce — so the
``activate()`` / ``pack()`` / ``finalize()`` paths are intentionally left
out of the unit-test coverage gate (see ``pyproject.toml``
``tool.coverage.report.omit``). The Python-level control flow is covered
by ``tests/domain/recon/test_structure_model.py``.
"""

from __future__ import annotations

import bisect
import logging
from collections.abc import Iterable
from typing import Any

import idaapi  # type: ignore[import-not-found]
from PySide6 import QtCore, QtGui

from .member import AbstractMember

logger = logging.getLogger(__name__)

# Sentinel "invalid" index. B008 forbids calling QtCore.QModelIndex() in a
# default-argument expression; hold it in a module-level singleton instead.
_INVALID_INDEX: QtCore.QModelIndex = QtCore.QModelIndex()

# Default name for the constructed structure (mirrors original
# ``TemporaryStructureModel.default_name``).
DEFAULT_STRUCT_NAME: str | None = None


class StructureModel(QtCore.QAbstractTableModel):
    """Qt table model for the structure builder.

    Columns: Offset, Type, Name, Comment. Items are :class:`AbstractMember`
    subclasses sorted by offset. Collision tracking is maintained alongside
    item insertion so the view can highlight overlapping candidates.
    """

    HEADERS = ["Offset", "Type", "Name", "Comment"]

    def __init__(
        self,
        items: list[AbstractMember] | None = None,
        templated_types: Any | None = None,
    ) -> None:
        super().__init__()
        self._items: list[AbstractMember] = list(items) if items else []
        self._items.sort(key=lambda m: m.offset)
        self.main_offset: int = 0
        self.tmpl_types = templated_types
        # collision[i] is True iff items[i] overlaps items[i+1] (offset range)
        self.collisions: list[bool] = [False] * len(self._items)
        self._refresh_collisions()

    # ------------------------------------------------------------------
    # Qt model API
    # ------------------------------------------------------------------
    def rowCount(  # noqa: N802 - Qt API override
        self,
        parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex = _INVALID_INDEX,
    ) -> int:
        return len(self._items)

    def columnCount(  # noqa: N802 - Qt API override
        self,
        parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex = _INVALID_INDEX,
    ) -> int:
        return len(self.HEADERS)

    def headerData(  # noqa: N802 - Qt API override
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if (
            role == QtCore.Qt.ItemDataRole.DisplayRole
            and orientation == QtCore.Qt.Orientation.Horizontal
        ):
            return self.HEADERS[section]
        return None

    def data(  # noqa: N802 - Qt API override
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        col = index.column()
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return f"0x{int(item.offset):04X} [{int(item.offset)}]"
            if col == 1:
                if getattr(item, "is_array", False) and int(getattr(item, "size", 0)) > 0:
                    arr_size = self.calculate_array_size(index.row())
                    if arr_size:
                        return f"{item.type_name}[{arr_size}]"
                return item.type_name
            if col == 2:
                return getattr(item, "name", "")
            if col == 3:
                return getattr(item, "cmt", "")
        elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
            if col == 0:
                return int(item.offset)
            if col == 1:
                return int(item.size) * (
                    self.calculate_array_size(index.row())
                    if getattr(item, "is_array", False)
                    else 1
                )
        elif role == QtCore.Qt.ItemDataRole.EditRole:
            if col == 2:
                return getattr(item, "name", "")
            if col == 3:
                return getattr(item, "cmt", "")
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            if col == 1:
                font = getattr(item, "font", None)
                return font if font is not None else None
        elif role == QtCore.Qt.ItemDataRole.BackgroundRole:
            if not getattr(item, "enabled", True):
                return QtGui.QColor(QtCore.Qt.GlobalColor.gray)
            if int(item.offset) == int(self.main_offset) and col == 0:
                return QtGui.QBrush(QtGui.QColor("#006699"))
            if self.have_collision(index.row()):
                return QtGui.QBrush(QtGui.QColor("#cc4b4b"))
        elif role == QtCore.Qt.ItemDataRole.ForegroundRole:
            if self.have_collision(index.row()):
                return QtGui.QBrush(QtGui.QColor("#f0db2b"))
        return None

    def setData(  # noqa: N802 - Qt API override
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        value: Any,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid() or index.row() >= len(self._items):
            return False
        row, col = index.row(), index.column()
        item = self._items[row]
        if col == 2 and role == QtCore.Qt.ItemDataRole.EditRole and idaapi.is_ident(str(value)):
            item.name = str(value)
            self.dataChanged.emit(index, index)
            return True
        if col == 3 and role == QtCore.Qt.ItemDataRole.EditRole:
            item.cmt = str(value)
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(  # noqa: N802 - Qt API override
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> QtCore.Qt.ItemFlag:
        base = super().flags(index)
        if index.column() in (2, 3):
            # PySide6 prefers explicit OR via ``.value`` for QFlags bitwise
            # operations (the bare ``|`` form triggers a RuntimeWarning under
            # PySide6 because the shim is PyQt5-only). We rebuild the ItemFlag
            # via union of integer values so the result is always a QFlags that
            # both PySide6 real environments and ``tools/mock_ida.py`` accept.
            def _qflag_int(flag: Any) -> int:
                value = getattr(flag, "value", None)
                if value is not None:
                    return int(value)
                # Some shims (mock_ida) don't expose ``.value`` — fall back to
                # the int() conversion that QFlags implements natively.
                fallback = int.__call__(flag)
                return int(fallback)

            return QtCore.Qt.ItemFlag(
                _qflag_int(base) | _qflag_int(QtCore.Qt.ItemFlag.ItemIsEditable)
            )
        return base

    # ------------------------------------------------------------------
    # Item management
    # ------------------------------------------------------------------
    def add_row(self, member: AbstractMember) -> None:
        """Insert ``member`` maintaining sorted order by offset; refresh collisions."""
        self.beginResetModel()  # noqa: N802 - Qt API
        keys = [m.offset for m in self._items]
        idx = bisect.bisect_left(keys, int(member.offset))
        self._items.insert(idx, member)
        self._refresh_collisions()
        self.endResetModel()  # noqa: N802 - Qt API

    def clear(self) -> None:
        self.beginResetModel()  # noqa: N802 - Qt API
        self._items = []
        self.collisions = []
        self.main_offset = 0
        self.endResetModel()  # noqa: N802 - Qt API

    @property
    def items(self) -> list[AbstractMember]:
        return list(self._items)

    def have_member(self, member: AbstractMember) -> bool:
        if not self._items:
            return False
        idx = bisect.bisect_left(self._items, member)
        if idx < len(self._items):
            return bool(self._items[idx] == member)
        return False

    def have_collision(self, row: int) -> bool:
        if 0 <= row < len(self.collisions):
            return bool(self.collisions[row])
        return False

    def _refresh_collisions(self) -> None:
        """Recompute ``self.collisions`` from ``self._items``.

        Mirrors the original's ``refresh_collisions``: walks pairs of
        enabled items in offset order; sets ``collisions[i]`` True when
        ``items[i]`` overlaps ``items[i+1]``.
        """
        self.collisions = [False] * len(self._items)
        if len(self._items) <= 1:
            return
        i = 0
        while i < len(self._items) - 1:
            cur = self._items[i]
            nxt = self._items[i + 1]
            if bool(getattr(cur, "enabled", True)) and bool(getattr(nxt, "enabled", True)):
                cur_end = int(cur.offset) + int(cur.size)
                if cur_end > int(nxt.offset):
                    self.collisions[i] = True
                    self.collisions[i + 1] = True
            i += 1

    # ------------------------------------------------------------------
    # Row operations — bound by Structure Builder buttons
    # ------------------------------------------------------------------
    def disable_rows(self, indices: Iterable[QtCore.QModelIndex]) -> None:
        for idx in indices:
            row = idx.row()
            if 0 <= row < len(self._items):
                self._items[row].set_enabled(False)
        self._refresh_collisions()
        self.layoutChanged.emit()

    def enable_rows(self, indices: Iterable[QtCore.QModelIndex]) -> None:
        for idx in indices:
            row = idx.row()
            if 0 <= row < len(self._items):
                self._items[row].set_enabled(True)
        self._refresh_collisions()
        self.layoutChanged.emit()

    def set_origin(self, indices: Iterable[QtCore.QModelIndex]) -> None:
        for idx in indices:
            row = idx.row()
            if 0 <= row < len(self._items):
                self.main_offset = int(self._items[row].offset)
        self.layoutChanged.emit()

    def make_array(self, indices: Iterable[QtCore.QModelIndex]) -> None:
        for idx in indices:
            row = idx.row()
            if 0 <= row < len(self._items):
                self._items[row].switch_array_flag()
        self.layoutChanged.emit()

    def remove_items(self, indices: Iterable[QtCore.QModelIndex]) -> None:
        rows = sorted(
            {idx.row() for idx in indices if 0 <= idx.row() < len(self._items)}, reverse=True
        )
        for row in rows:
            del self._items[row]
        self._refresh_collisions()
        self.layoutChanged.emit()

    def activated(self, index: QtCore.QModelIndex | QtCore.QPersistentModelIndex) -> None:
        """Double-click handler: ask user to edit a member's type in-place."""
        if not index.isValid() or index.column() != 1:
            return
        row = index.row()
        if 0 <= row >= len(self._items):
            return
        item = self._items[row]
        activate = getattr(item, "activate", None)
        if activate is not None:
            activate(self)

    # ------------------------------------------------------------------
    # Substructure packing / unpacking — depends on Hex-Rays UDT APIs
    # ------------------------------------------------------------------
    def get_next_enabled(self, row: int) -> int:
        """Return the index of the next enabled item after ``row``.

        Returns ``len(self._items)`` if no more enabled items follow.
        """
        for i in range(row + 1, len(self._items)):
            if bool(getattr(self._items[i], "enabled", True)):
                return i
        return len(self._items)

    def have_member_at(self, offset: int) -> bool:
        return any(int(m.offset) == int(offset) for m in self._items)

    def have_collision_at(self, row: int) -> bool:
        return self.have_collision(row)

    def calculate_array_size(self, row: int) -> int:
        """Count enabled same-type members packed contiguously starting at ``row``.

        Mirrors original ``calculate_array_size``: walks forward from ``row``,
        gathering enabled items with the same ``type_name`` whose offset is
        exactly ``prev.offset + prev.size`` — returns the count including
        the starting row.
        """
        if row < 0 or row >= len(self._items):
            return 0
        first = self._items[row]
        if not bool(getattr(first, "enabled", True)):
            return 0
        size = int(first.size) or 1
        count = 1
        offset = int(first.offset) + size
        i = row + 1
        while i < len(self._items):
            nxt = self._items[i]
            if not bool(getattr(nxt, "enabled", True)):
                i += 1
                continue
            if int(nxt.offset) != offset or nxt.type_name != first.type_name:
                break
            count += 1
            offset += int(nxt.size) or 1
            i += 1
        return count

    def get_unique_scanned_variables(self, origin: int = 0) -> list[Any]:
        """Collect unique ``scanned_variables`` from items with matching ``origin``.

        Used by finalize()/set_decl() to find the variables to re-apply
        the newly-constructed type to.
        """
        seen: set[int] = set()
        result: list[Any] = []
        for item in self._items:
            if int(getattr(item, "origin", 0)) != int(origin):
                continue
            for var in getattr(item, "scanned_variables", set()):
                key = id(var)
                if key in seen:
                    continue
                seen.add(key)
                result.append(var)
        return result

    def get_recognized_shape(self, start: int = 0, stop: int = -1) -> Any:
        """Build a UDT tinfo from the enabled items in ``items[start:stop]``.

        Returns ``None`` if no enabled items exist. Mirrors the original
        ``TemporaryStructureModel.get_recognized_shape`` — builds one
        ``udm_t`` per enabled item, with offset/size taken from the item
        and type from ``item.tinfo``.

        ``start:stop`` are indices into the sorted items array. Default
        ``(0, -1)`` means the full range.
        """
        end = stop if stop != -1 else len(self._items)
        enabled = [m for m in self._items[start:end] if bool(getattr(m, "enabled", True))]
        if not enabled:
            return None
        udt = idaapi.udt_type_data_t()
        for item in enabled:
            udm = idaapi.udm_t()
            udm.offset = int(item.offset) * 8
            udm.name = str(getattr(item, "name", ""))
            udm.type = getattr(item, "tinfo", None)
            udm.size = (
                int(getattr(item, "size", 0)) if getattr(item, "tinfo", None) is not None else 0
            )
            udt.push_back(udm)
        tinfo = idaapi.tinfo_t()
        tinfo.create_udt(udt, idaapi.BTF_STRUCT)
        return tinfo

    # ------------------------------------------------------------------
    # finalize / pack / resolve_types / load_struct — require IDA UDT APIs
    # ------------------------------------------------------------------
    def get_name(self) -> str | None:
        """Derive a structure name from virtual tables in the model.

        Mirrors original: walks items, returns the first vtable's
        ``vtable_name`` (with ``_vtbl`` stripped) if any vtables have a
        nice name; otherwise ``DEFAULT_STRUCT_NAME``.
        """
        candidate: str | None = None
        for field in self._items:
            if field.__class__.__name__ == "DiscoveredVTable":
                have_nice = bool(getattr(field, "have_nice_name", False))
                if have_nice:
                    if candidate is not None:
                        logger.warning(
                            "Structure has 2 or more virtual tables; name set to default"
                        )
                        return DEFAULT_STRUCT_NAME
                    candidate = getattr(field, "vtable_name", "").replace("_vtbl", "")
        return candidate or DEFAULT_STRUCT_NAME

    def finalize(self) -> Any:
        """Build a structure from the current items and create it in Local Types.

        Mirrors ``TemporaryStructureModel.finalize`` (which is currently
        a stub in the original — actual implementation is in ``pack``).
        Calls ``pack`` with the full range and returns the resulting tinfo.
        """
        return self.pack(0, None)

    def pack(self, start: int = 0, stop: int | None = None) -> Any:
        """Build a packed structure from ``items[start:stop]``.

        Filters out disabled items; computes gap padding between items;
        prompts the user for a struct name if none can be derived; builds
        the UDT; asks the user to confirm the C declaration; and calls
        ``set_decl`` to install it and apply types to scanned variables.

        ``stop=None`` means "until the next disabled member or end".
        """
        if stop is None:
            stop = self.get_next_enabled(start)
        if any(self.collisions[start:stop]):
            logger.warning("Collisions detected")
            return None
        struct_name = self.get_name()
        if not struct_name:
            struct_name = idaapi.ask_str("", idaapi.HIST_TYPE, "Struct name:")
            if not struct_name:
                return None
        origin = int(self._items[start].offset) if start < len(self._items) else 0
        final_tinfo = idaapi.tinfo_t()
        udt_data = idaapi.udt_type_data_t()
        offset = origin
        for item in [x for x in self._items[start:stop] if bool(getattr(x, "enabled", True))]:
            gap = int(item.offset) - offset
            if gap:
                from ..types.udt_builder import create_padding_udt_member

                udt_data.push_back(create_padding_udt_member(offset - origin, gap))
            if bool(getattr(item, "is_array", False)):
                arr_size = self.calculate_array_size(bisect.bisect_left(self._items, item))
                if arr_size:
                    member = item.get_udt_member(arr_size, offset=origin)
                    if member is not None:
                        udt_data.push_back(member)
                        offset = int(item.offset) + int(item.size) * arr_size
                        continue
            member = item.get_udt_member(offset=origin)
            if member is not None:
                udt_data.push_back(member)
                offset = int(item.offset) + int(item.size)
        final_tinfo.create_udt(udt_data, idaapi.BTF_STRUCT)
        cdecl = idaapi.print_tinfo(
            None,
            4,
            5,
            idaapi.PRTYPE_MULTI | idaapi.PRTYPE_TYPE | idaapi.PRTYPE_SEMI,
            final_tinfo,
            struct_name,
            None,
        )
        cdecl = idaapi.ask_text(
            0x10000, "#pragma pack(push, 1)\n" + cdecl, "The following new type will be created"
        )
        if cdecl:
            return self.set_decl(cdecl, origin)
        logger.error("No declaration for structure set")
        return None

    def set_decl(self, cdecl: str, origin: int = 0) -> Any:
        """Parse ``cdecl`` and create the type; apply it to scanned variables.

        Mirrors ``TemporaryStructureModel.set_decl``.
        """
        from ..til.type_library import create_type

        parse_result = idaapi.idc_parse_decl(idaapi.get_idati(), cdecl, idaapi.PT_TYP)
        if not parse_result:
            logger.error("Could not parse structure declaration")
            return None
        structure_name = parse_result[0]
        if create_type(structure_name, cdecl):
            logger.info("Structure %r was added to Local Types", structure_name)
            tinfo = idaapi.create_typedef(structure_name)
            ptr_tinfo = idaapi.tinfo_t()
            ptr_tinfo.create_ptr(tinfo)
            for scanned_var in self.get_unique_scanned_variables(origin):
                scanned_var.apply_type(ptr_tinfo)
            return tinfo
        logger.error("Structure %r probably already exists", structure_name)
        return None

    def pack_substructure(self, indices: Iterable[QtCore.QModelIndex]) -> None:
        """Pack selected items into a sub-structure.

        Stubbed for the port: the original opens an ``ask_text`` dialog to
        name the sub-structure and inserts a ``Member`` referencing it at
        the lowest selected offset, removing the originals. End-to-end
        verification requires real IDA — out of unit-test scope.
        """
        rows = sorted({idx.row() for idx in indices if 0 <= idx.row() < len(self._items)})
        if not rows:
            return
        logger.debug("pack_substructure requested for rows %s", rows)

    def unpack_substructure(self, indices: Iterable[QtCore.QModelIndex]) -> None:
        """Unpack a sub-structure — replace a struct member with its UDT members.

        Stubbed for the port. Requires Hex-Rays UDT introspection on the
        selected member's type; left out of unit-test scope.
        """
        rows = sorted({idx.row() for idx in indices if 0 <= idx.row() < len(self._items)})
        if not rows:
            return
        logger.debug("unpack_substructure requested for rows %s", rows)

    def resolve_types(self) -> None:
        """Resolve user-entered type strings into real tinfos.

        Stubbed for the port: original uses ``idc.parse_decl`` + ``tinfo.deserialize``
        to convert text in member ``name``/``cmt`` columns into concrete types.
        """
        logger.debug("resolve_types requested")

    def load_struct(self) -> None:
        """Replace the current items with members of an existing Local Type.

        Stubbed for the port: original opens a chooser of all local UDTs and
        loads the selected struct's members as items. Requires real IDA.
        """
        logger.debug("load_struct requested")

    def recognize_shape(self, indices: Iterable[QtCore.QModelIndex]) -> None:
        """Open the chooser for the user to pick a shape to apply to selection.

        Stubbed for the port: original calls ``VariableScanner.NewShallowSearchVisitor``
        on the structure with origin=0. End-to-end requires Hex-Rays ctree.
        """
        rows = sorted({idx.row() for idx in indices if 0 <= idx.row() < len(self._items)})
        if not rows:
            return
        logger.debug("recognize_shape requested for rows %s", rows)

    def set_stl_type(self, key: str, args: tuple[str, ...]) -> None:
        """Apply a templated (STL) type with user-supplied args.

        Stubbed for the port: original uses the templated_types TOML config
        to format the type with `args` and adds it to Local Types.
        """
        if self.tmpl_types is None:
            logger.warning("set_stl_type called but tmpl_types is None")
            return
        struct_str = self.tmpl_types.get_struct(key)
        if struct_str is None:
            logger.warning("Unknown templated type key %r", key)
            return
        logger.debug("set_stl_type: key=%r args=%r", key, args)
