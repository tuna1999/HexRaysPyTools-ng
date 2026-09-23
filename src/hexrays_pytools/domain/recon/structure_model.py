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

from .member import AbstractMember, Member

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
        self._items.sort()
        self.main_offset: int = 0
        self.default_name: str | None = DEFAULT_STRUCT_NAME
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
        if self.have_member(member):
            return
        self.beginResetModel()  # noqa: N802 - Qt API
        idx = bisect.bisect_left(self._items, member)
        self._items.insert(idx, member)
        self._refresh_collisions()
        self.endResetModel()  # noqa: N802 - Qt API

    def clear(self) -> None:
        self.beginResetModel()  # noqa: N802 - Qt API
        self._items = []
        self.collisions = []
        self.main_offset = 0
        self.default_name = DEFAULT_STRUCT_NAME
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
        enabled_rows = [i for i, item in enumerate(self._items) if bool(item.enabled)]
        if len(enabled_rows) <= 1:
            return

        current_pos = 0
        while current_pos < len(enabled_rows) - 1:
            current_row = enabled_rows[current_pos]
            current = self._items[current_row]
            next_pos = current_pos + 1
            while next_pos < len(enabled_rows):
                next_row = enabled_rows[next_pos]
                nxt = self._items[next_row]
                current_end = int(current.offset) + int(current.size)
                if current_end > int(nxt.offset):
                    self.collisions[current_row] = True
                    self.collisions[next_row] = True
                    if current_end < int(nxt.offset) + int(nxt.size):
                        current_pos = next_pos
                        break
                else:
                    current_pos = next_pos
                    break
                next_pos += 1
            else:
                break

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
        """Double-click handler for scan origins (col 0) and member types (col 1)."""
        if not index.isValid():
            return
        row = index.row()
        if not (0 <= row < len(self._items)):
            return
        item = self._items[row]
        if index.column() == 0:
            scanned_variables = list(getattr(item, "scanned_variables", set()))
            if not scanned_variables:
                return
            from ..chooser import MyChoose

            chooser = MyChoose(
                [x.to_list() for x in scanned_variables],
                "Select Variable",
                [["Origin", 4], ["Function name", 25], ["Variable name", 25], ["Expression address", 10]],
            )
            selected = chooser.Show(True)
            if selected is not None and 0 <= int(selected) < len(scanned_variables):
                idaapi.open_pseudocode(int(scanned_variables[int(selected)].expression_address), 0)
        elif index.column() == 1:
            activate = getattr(item, "activate", None)
            if activate is not None:
                activate(self)

    # ------------------------------------------------------------------
    # Substructure packing / unpacking — depends on Hex-Rays UDT APIs
    # ------------------------------------------------------------------
    def get_next_enabled(self, row: int) -> int:
        """Return the index of the next enabled item after ``row``.

        Returns ``-1`` if no more enabled items follow.
        """
        for i in range(row + 1, len(self._items)):
            if bool(getattr(self._items[i], "enabled", True)):
                return i
        return -1

    def have_member_at(self, offset: int) -> bool:
        return any(int(m.offset) == int(offset) for m in self._items)

    def have_collision_at(self, row: int) -> bool:
        return self.have_collision(row)

    def calculate_array_size(self, row: int) -> int:
        """Infer array length from the distance to the next enabled member."""
        if row < 0 or row >= len(self._items):
            return 0
        first = self._items[row]
        if not bool(getattr(first, "enabled", True)):
            return 0
        next_row = self.get_next_enabled(row)
        if next_row < 0:
            return 0
        size = int(first.size)
        if size <= 0:
            return 0
        return (int(self._items[next_row].offset) - int(first.offset)) // size

    def get_unique_scanned_variables(self, origin: int = 0) -> list[Any]:
        """Collect unique ``scanned_variables`` from items with matching ``origin``.

        Used by finalize()/set_decl() to find the variables to re-apply
        the newly-constructed type to.
        """
        seen: set[Any] = set()
        result: list[Any] = []
        for item in self._items:
            if int(getattr(item, "origin", 0)) != int(origin):
                continue
            for var in getattr(item, "scanned_variables", set()):
                key: Any = (
                    getattr(var, "function_name", None),
                    getattr(var, "name", None),
                )
                if key == (None, None):
                    key = id(var)
                if key in seen:
                    continue
                seen.add(key)
                result.append(var)
        return result

    def get_recognized_shape(self, start: int = 0, stop: int = -1) -> Any:
        """Find an existing Local Type whose fields match the selected shape."""
        if not self._items:
            return None
        if stop != -1:
            base = int(self._items[start].offset)
            enabled = [x for x in self._items[start:stop] if bool(x.enabled)]
        else:
            base = 0
            enabled = [x for x in self._items if bool(x.enabled)]
        if not enabled:
            return None

        min_size = int(enabled[-1].offset) + int(enabled[-1].size) - base
        offsets = {int(x.offset) for x in enabled}
        matches: list[tuple[int, Any]] = []
        for ordinal in range(1, int(idaapi.get_ordinal_count())):
            tinfo = idaapi.tinfo_t()
            if not tinfo.get_numbered_type(idaapi.get_idati(), ordinal):
                continue
            if not tinfo.is_udt() or int(tinfo.get_size()) < min_size:
                continue
            udt = idaapi.udt_type_data_t()
            if not tinfo.get_udt_details(udt):
                continue
            by_offset: dict[int, list[Any]] = {}
            for field in udt:
                by_offset.setdefault(int(field.offset) // 8, []).append(field.type)

            found = True
            for absolute_offset in offsets:
                candidates = [x for x in enabled if int(x.offset) == absolute_offset]
                potential = by_offset.get(absolute_offset - base, [])
                if not any(
                    item.type_equals_to(field_type)
                    for item in candidates
                    for field_type in potential
                ):
                    found = False
                    break
            if found:
                matches.append((ordinal, idaapi.tinfo_t(tinfo)))

        if not matches:
            return None
        from ..chooser import MyChoose

        chooser = MyChoose(
            [[str(o), f"0x{int(t.get_size()):08X}", str(t.dstr())] for o, t in matches],
            "Select Structure",
            [["Ordinal", 5], ["Size", 10], ["Structure name", 50]],
        )
        idx = chooser.Show(True)
        if idx is not None and 0 <= int(idx) < len(matches):
            return matches[int(idx)][1]
        return None

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
        return candidate or self.default_name

    def finalize(self) -> Any:
        """Build a structure from the current items and create it in Local Types.

        Mirrors ``TemporaryStructureModel.finalize`` (which is currently
        a stub in the original — actual implementation is in ``pack``).
        Calls ``pack`` with the full range and returns the resulting tinfo.
        """
        result = self.pack(0, None)
        if result is not None:
            self.clear()
        return result

    def pack(self, start: int = 0, stop: int | None = None) -> Any:
        """Build a packed structure from ``items[start:stop]``.

        Filters out disabled items; computes gap padding between items;
        prompts the user for a struct name if none can be derived; builds
        the UDT; asks the user to confirm the C declaration; and calls
        ``set_decl`` to install it and apply types to scanned variables.

        ``stop=None`` means the full remaining range, matching the original.
        """
        end = len(self._items) if stop is None else stop
        if not self._items or start < 0 or start >= end or start >= len(self._items):
            return None
        if any(self.collisions[start:end]):
            logger.warning("Collisions detected")
            return None
        struct_name = self.get_name()
        if not struct_name:
            struct_name = idaapi.ask_str("", idaapi.HIST_TYPE, "Struct name:")
            if not struct_name:
                return None
        origin = int(self._items[start].offset) if start else 0
        final_tinfo = idaapi.tinfo_t()
        udt_data = idaapi.udt_type_data_t()
        offset = origin
        for item in [x for x in self._items[start:end] if bool(getattr(x, "enabled", True))]:
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
        """Pack the selected contiguous row range into a new UDT member."""
        rows = sorted({idx.row() for idx in indices if 0 <= idx.row() < len(self._items)})
        if not rows:
            return
        start, stop = rows[0], rows[-1] + 1
        tinfo = self.pack(start, stop)
        if tinfo is None:
            return
        offset = int(self._items[start].offset)
        self.beginResetModel()
        del self._items[start:stop]
        keys = [m.offset for m in self._items]
        insert_at = bisect.bisect_left(keys, offset)
        self._items.insert(insert_at, Member(offset=offset, tinfo=tinfo))
        self._refresh_collisions()
        self.endResetModel()

    def unpack_substructure(self, indices: Iterable[QtCore.QModelIndex]) -> None:
        """Replace one UDT member with its constituent members."""
        rows = sorted({idx.row() for idx in indices if 0 <= idx.row() < len(self._items)})
        if len(rows) != 1:
            return
        row = rows[0]
        item = self._items[row]
        if item.tinfo is None or not bool(item.tinfo.is_udt()):
            return

        udt_data = idaapi.udt_type_data_t()
        if not item.tinfo.get_udt_details(udt_data):
            return

        expanded: list[AbstractMember] = []
        base = int(item.offset)
        for udm in udt_data:
            member = Member(
                offset=base + int(udm.offset) // 8,
                tinfo=udm.type,
                name=str(udm.name),
                cmt=str(getattr(udm, "cmt", "") or ""),
            )
            expanded.append(member)

        self.beginResetModel()
        del self._items[row]
        self._items.extend(expanded)
        self._items.sort(key=lambda m: int(m.offset))
        self._refresh_collisions()
        self.endResetModel()

    def resolve_types(self) -> None:
        """Disable lower-scoring candidates that collide with better ones,
        then subsume static element accesses into discovered arrays."""
        current_item: AbstractMember | None = None
        current_score = 0
        for item in self._items:
            if not bool(item.enabled):
                continue
            if current_item is None:
                current_item = item
                current_score = int(item.score)
                continue

            item_score = int(item.score)
            if current_item.has_collision(item):
                # Upstream keeps the higher-scoring candidate when two
                # enabled members collide.
                if item_score <= current_score:
                    item.set_enabled(False)
                    continue
                current_item.set_enabled(False)
            current_item = item
            current_score = item_score

        self._subsume_array_elements()
        self._pack_contiguous_colocations()
        self._refresh_collisions()
        self.layoutChanged.emit()

    def _subsume_array_elements(self) -> None:
        """Fold static element accesses into discovered arrays.

        TRex §3.3.4 aggregate analysis: when dynamic-index evidence produced
        an array member at offset X with element size E, a static member at
        X + k*E (k >= 1) of the same width is an element of that array, not
        a distinct field — disable it so the flat model doesn't emit phantom
        scalar fields inside the array run. Only concrete ``Member`` arrays
        participate (``VoidMember`` byte-runs are a different concept).
        """
        arrays = [
            item
            for item in self._items
            if bool(item.enabled)
            and isinstance(item, Member)
            and bool(item.is_array)
            and int(item.size) in (2, 4, 8)
        ]
        if not arrays:
            return
        for item in self._items:
            if not bool(item.enabled) or item in arrays:
                continue
            for arr in arrays:
                elem = int(arr.size)
                delta = int(item.offset) - int(arr.offset)
                if delta >= elem and delta % elem == 0 and int(item.size) == elem:
                    item.set_enabled(False)
                    break

    def _pack_contiguous_colocations(self) -> None:
        """Pack adjacent same-width members sharing a scanned origin.

        TRex §3.3.4 aggregate analysis: two contiguous members of the same
        width W at offsets (X, W) and (X+W, W) that share at least one
        ``scanned_variables`` element (they came from the same sub-region
        scan — e.g. ``helper(&p->u)`` for both, or repeated ``a1[k].x``
        scans) form a sub-struct at (X, 2W). This resolves the flat
        model's §2.2 ambiguity when colocation evidence is strong. A
        local UDT tinfo is built (no global Local Types mutation, no
        ``apply_type`` on scanned vars) so the bench can scan multiple
        structs without cross-contamination. Disabled items break the
        chain; arrays are not packed (their element semantics differ).
        Iterates until no more pairs qualify.
        """
        packed = True
        while packed:
            packed = False
            items = self._items
            for i in range(len(items) - 1):
                a = items[i]
                b = items[i + 1]
                if not (bool(a.enabled) and bool(b.enabled)):
                    continue
                if not (isinstance(a, Member) and isinstance(b, Member)):
                    continue
                wa = int(a.size)
                wb = int(b.size)
                if wa != wb or wa not in (2, 4, 8):
                    continue
                if int(b.offset) != int(a.offset) + wa:
                    continue
                if int(getattr(a, "origin", 0)) != int(getattr(b, "origin", 0)):
                    continue
                # Only pack when the scanned origin is non-zero (a sub-region
                # scan like ``helper(&p->u)`` proves the members live inside a
                # sub-struct). A top-level scan at origin 0 produces members
                # of the outer struct — packing two dwords into a sub-struct
                # there would contradict a flat decomposition the scanner has
                # no evidence against (TRex §2.2 confounding stack shape).
                if int(getattr(a, "origin", 0)) <= 0:
                    continue
                sa = self._scanned_origin_keys(a)
                sb = self._scanned_origin_keys(b)
                if not sa or not sb or not (sa & sb):
                    continue
                # Restrict packing to plain integer primitives. Pointers,
                # function pointers, UDTs and strings are independent fields
                # of the parent struct, not members of a sub-structure — a
                # funcptr and a pointer-sized slot next to it are siblings,
                # not a two-field sub-struct (TRex aggregate analysis).
                try:
                    if not (
                        bool(a.tinfo.is_integral())
                        and not bool(a.tinfo.is_ptr())
                        and not bool(a.tinfo.is_funcptr())
                        and bool(b.tinfo.is_integral())
                        and not bool(b.tinfo.is_ptr())
                        and not bool(b.tinfo.is_funcptr())
                    ):
                        continue
                except (AttributeError, RuntimeError, TypeError):
                    continue
                udt = idaapi.tinfo_t()
                udt_data = idaapi.udt_type_data_t()
                base = int(a.offset)
                ok = True
                for m in (a, b):
                    um = m.get_udt_member(offset=base)
                    if um is None:
                        ok = False
                        break
                    udt_data.push_back(um)
                if not ok or not udt.create_udt(udt_data, idaapi.BTF_STRUCT):
                    continue
                packed_member = Member(offset=base, tinfo=udt)
                packed_member.scanned_variables = set(a.scanned_variables) | set(b.scanned_variables)
                packed_member.origin = int(getattr(a, "origin", 0))
                self.beginResetModel()
                del items[i : i + 2]
                keys = [m.offset for m in items]
                items.insert(bisect.bisect_left(keys, base), packed_member)
                self._refresh_collisions()
                self.endResetModel()
                packed = True
                break

    @staticmethod
    def _scanned_origin_keys(member: AbstractMember) -> set[tuple[int, str, int]]:
        """Equivalence key for a member's ``scanned_variables``.

        ``ScannedObject.__eq__`` hashes by ``(func_ea, name, expression_address)``
        — two stores of the same lvar at different lines produce distinct
        instances, so a naive set intersection misses shared origin. We
        collapse on ``(func_ea, name, origin)`` so members extracted from
        the same lvar at the same sub-offset (e.g. ``helper_unit(&p->u)``'s
        ``u->x`` and ``u->y``) compare equal.
        """
        keys: set[tuple[int, str, int]] = set()
        for sv in getattr(member, "scanned_variables", set()):
            keys.add(
                (
                    int(getattr(sv, "func_ea", 0)),
                    str(getattr(sv, "name", "")),
                    int(getattr(sv, "origin", 0)),
                )
            )
        return keys

    def load_struct(self) -> None:
        """Load members from a named UDT in Local Types into the model."""
        name = ""
        tinfo = idaapi.tinfo_t()
        while True:
            entered = idaapi.ask_str(name, idaapi.HIST_TYPE, "Enter type:")
            if entered is None:
                return
            name = str(entered)
            if tinfo.get_named_type(idaapi.get_idati(), name) and bool(tinfo.is_udt()):
                break
            logger.warning("Invalid UDT name: %s", name)

        udt_data = idaapi.udt_type_data_t()
        if not tinfo.get_udt_details(udt_data):
            return

        loaded: list[AbstractMember] = []
        for udm in udt_data:
            offset = int(udm.offset) // 8
            member_name = str(udm.name)
            if member_name == f"gap_{offset:X}":
                continue
            loaded.append(
                Member(
                    offset=offset,
                    tinfo=udm.type,
                    name=member_name,
                    cmt=str(getattr(udm, "cmt", "") or f"imported from {name}"),
                )
            )

        self.beginResetModel()
        self._items.extend(loaded)
        self._items.sort()
        self.default_name = name
        self._refresh_collisions()
        self.endResetModel()

    def recognize_shape(self, indices: Iterable[QtCore.QModelIndex]) -> None:
        """Apply the inferred UDT shape to scanned variables and selected range."""
        valid = [idx for idx in indices if 0 <= idx.row() < len(self._items)]
        rows = sorted({idx.row() for idx in valid})
        if not rows:
            return
        if len(rows) == 1:
            tinfo = self.get_recognized_shape()
            if tinfo is None:
                return
            ptr_tinfo = idaapi.tinfo_t()
            ptr_tinfo.create_ptr(tinfo)
            for scanned_var in self.get_unique_scanned_variables(origin=0):
                scanned_var.apply_type(ptr_tinfo)
            self.clear()
            return

        start, stop = rows[0], rows[-1] + 1
        base = int(self._items[start].offset)
        tinfo = self.get_recognized_shape(start, stop)
        if tinfo is None:
            return
        ptr_tinfo = idaapi.tinfo_t()
        ptr_tinfo.create_ptr(tinfo)
        for scanned_var in self.get_unique_scanned_variables(base):
            scanned_var.apply_type(ptr_tinfo)

        size = int(tinfo.get_size())
        self.beginResetModel()
        self._items = [x for x in self._items if int(x.offset) < base or int(x.offset) >= base + size]
        keys = [m.offset for m in self._items]
        insert_at = bisect.bisect_left(keys, base)
        self._items.insert(insert_at, Member(offset=base, tinfo=tinfo))
        self._refresh_collisions()
        self.endResetModel()

    def set_decls(self, base_struct_name: str, cdecls: str) -> Any:
        """Parse multiple declarations, load the base type, and apply its pointer."""
        errors = int(idaapi.idc_parse_types(cdecls, 0))
        if errors != 0:
            logger.error("Could not parse structure declarations: %d errors", errors)
            return None

        tinfo = idaapi.tinfo_t()
        if not tinfo.get_named_type(idaapi.get_idati(), base_struct_name):
            logger.error("Parsed declarations but base type %r was not created", base_struct_name)
            return None

        ptr_tinfo = idaapi.tinfo_t()
        if not ptr_tinfo.create_ptr(tinfo):
            return None
        for scanned_var in self.get_unique_scanned_variables():
            scanned_var.apply_type(ptr_tinfo)
        return tinfo

    def set_stl_type(self, key: str, args: tuple[str, ...]) -> None:
        """Render and install one configured templated/STL type."""
        if self.tmpl_types is None:
            logger.warning("set_stl_type called but tmpl_types is None")
            return
        result = self.tmpl_types.get_decl_str(key, list(args))
        if not result.is_ok:
            logger.error("Could not generate templated type %r: %s", key, result.error)
            return
        name, cdecl = result.unwrap()
        if self.set_decls(name, cdecl) is not None:
            self.clear()
