"""Struct member candidate data classes.

Ported from ``refs/HexRaysPyTools/HexRaysPyTools/core/temporary_structure.py``
(``AbstractMember``, ``Member``, ``VoidMember``).

The original classes were free-form ``object`` subclasses with rich
behaviour (score, font, cmt, set_enabled, switch_array_flag, has_collision).
This port uses :class:`dataclass` for value semantics + the
``StructureModel`` calls ``getattr(item, ...)`` defensively so missing
attributes (e.g. ``font`` on a plain :class:`Member`) don't crash.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _make_byte_tinfo() -> Any:
    """Build a ``_BYTE`` (unsigned byte) IDA tinfo, robust to API drift.

    IDA 9.4 ``tinfo_t(BTF_BYTE)`` already produces a ``_BYTE`` — calling
    ``create_simple_type(BT_BTY | BTS_BYTE)`` afterwards triggers an
    ``OverflowError: argument 2 of type 'type_t'`` because the
    composition flag is no longer a valid input.

    Older IDA versions (7.x / 8.x) accept the same two-step pattern.
    We try ``tinfo_t(BTF_BYTE)`` alone first, then optionally refine
    via ``create_simple_type`` only if the type is empty afterwards.
    """
    try:
        import idaapi  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        bt_byte = int(getattr(idaapi, "BTF_BYTE", 0))
        ti = idaapi.tinfo_t(bt_byte)
        # If the tinfo already describes a byte (after construction), we're
        # done — don't call create_simple_type, the API doesn't accept
        # the bitflag composition in IDA 9.4.
        try:
            size = int(ti.get_size()) if hasattr(ti, "get_size") else 0
        except Exception:  # noqa: BLE001
            size = 0
        if size == 1:
            return ti
        # Fallback for IDA 7.x / 8.x — some versions require the
        # explicit ``create_simple_type(BT_BTY | BTS_BYTE)``.
        if hasattr(ti, "create_simple_type"):
            bt_bty = getattr(idaapi, "BT_BTY", None)
            bts_byte = getattr(idaapi, "BTS_BYTE", None)
            if isinstance(bt_bty, int) and isinstance(bts_byte, int):
                import contextlib

                with contextlib.suppress(Exception):
                    ti.create_simple_type(bt_bty | bts_byte)
        return ti
    except (AttributeError, RuntimeError, TypeError, OverflowError):
        return None


@dataclass
class AbstractMember:
    """Base class for a struct member candidate."""

    offset: int
    tinfo: Any = None
    name: str = ""
    cmt: str = ""
    origin: int = 0
    enabled: bool = True
    is_array: bool = False
    scanned_variables: set[int] = field(default_factory=set)

    @property
    def size(self) -> int:
        if self.tinfo is None:
            return 0
        try:
            return int(self.tinfo.get_size())
        except (AttributeError, RuntimeError):
            return 0

    @property
    def type_name(self) -> str:
        if self.tinfo is None:
            return self.name or "void"
        return str(getattr(self.tinfo, "dstr", lambda: self.name)())

    def set_enabled(self, enable: bool) -> None:
        """Toggle enabled state; clearing the array flag (mirrors original)."""
        self.enabled = bool(enable)
        if not self.enabled:
            self.is_array = False

    def switch_array_flag(self) -> None:
        """Toggle ``is_array`` (VoidMember overrides to no-op)."""
        self.is_array = not self.is_array

    def font(self) -> Any:
        """Return a QFont for the row (None means default). Subclasses override."""
        return None

    def has_collision(self, other: AbstractMember) -> bool:
        """True iff this member's offset range overlaps ``other``'s."""
        self_end = int(self.offset) + int(self.size)
        other_end = int(other.offset) + int(other.size)
        if int(self.offset) <= int(other.offset):
            return self_end > int(other.offset)
        return other_end >= int(self.offset)

    def get_udt_member(self, array_size: int = 0, offset: int = 0) -> Any:
        """Build an ``idaapi.udt_member_t`` from this member.

        Mirrors original ``Member.get_udt_member``. ``offset`` is the
        base offset to subtract from ``self.offset`` to make the member
        relative to its containing structure.

        If ``self.tinfo`` is ``None`` (e.g. a :class:`VoidMember` built
        without ``BYTE_TINFO`` injection), the member is rendered as a
        single ``_BYTE`` (``idaapi.BT_BTY``) so IDA can still embed it
        in the UDT — matching the original which always passes a real
        tinfo to VoidMember.
        """
        import re as _re

        import idaapi

        udt_member = idaapi.udt_member_t()
        # Mirrors original: only rewrite auto-generated names like
        # ``byte_0``, ``dword_10``; leave user-renamed fields alone.
        auto_name_re = _re.compile(r"(byte|(d|q|t|dq|)word|float|(d|dd)ouble)_")
        if auto_name_re.match(self.name or ""):
            operand = self.type_name.replace("[", "").replace("]", "").replace("*", "").strip()
            udt_member.name = f"{operand}_{int(self.offset) - int(offset):x}"
        else:
            udt_member.name = self.name
        # IDA rejects ``None`` (``udm_t_type_set`` requires a real tinfo_t *).
        # Fall back to a single-byte type so the member still fits.
        # The byte-type constants (``BT_BTY``, ``BTS_BYTE``) and the
        # ``create_simple_type`` API differ slightly between IDA 7.x,
        # 8.x and 9.x — try the modern API first, then the legacy ones,
        # then a pure ``tinfo_t(BTF_BYTE)`` no-op as the last resort.
        member_tinfo = self.tinfo
        if member_tinfo is None:
            member_tinfo = _make_byte_tinfo()
            if member_tinfo is None:
                # Even the byte tinfo couldn't be built (mock env, stripped
                # IDA stub). Caller skips the member.
                return None
        udt_member.type = member_tinfo
        if array_size:
            tmp = idaapi.tinfo_t(member_tinfo)
            tmp.create_array(member_tinfo, array_size)
            udt_member.type = tmp
        udt_member.offset = int(self.offset) - int(offset)
        udt_member.size = int(self.size)
        return udt_member

    def activate(self, model: Any) -> None:
        """Default activate() — prompt the user to replace the member's type."""
        import idaapi
        import idc  # type: ignore[import-not-found]

        new_decl = idaapi.ask_str(self.type_name, 0x100, "Enter type:")
        if new_decl is None:
            return
        result = idc.parse_decl(new_decl, 0)
        if result is None:
            return
        _, tp, fld = result
        tinfo = idaapi.tinfo_t()
        tinfo.deserialize(idaapi.get_idati(), tp, fld, None)
        self.tinfo = tinfo
        self.is_array = False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AbstractMember):
            return NotImplemented
        # Merge scanned_variables on match (original plugin behavior)
        if self.offset == other.offset and self.size == other.size:
            self.scanned_variables |= other.scanned_variables
            return True
        return False

    def __hash__(self) -> int:
        return hash((self.offset, self.size))

    def __lt__(self, other: AbstractMember) -> bool:
        # Pure offset comparison — type_name can be a MagicMock or other
        # non-comparable object, and we only need a stable order for
        # ``bisect.insort`` to find the right insertion point. Items with
        # the same offset are treated as equal, which is fine for the
        # model's sorted-by-offset invariant.
        return int(self.offset) < int(other.offset)

    @property
    def score(self) -> int:
        """Likelihood this member is the right candidate for its offset.

        Mirrors original ``AbstractMember.score`` (``core/temporary_structure.py:198-206``).
        Higher = better candidate. Used by ``StructureModel.resolve_types``
        to cull the worst candidates.

        Falls back to ``0xFFFF`` (worst) when the tinfo is unparseable —
        matches the original.
        """
        try:
            from ...pure.scoring import score_member  # noqa: PLC0415

            name = self.type_name
            if name and isinstance(name, str) and not name.startswith("_"):
                try:
                    type_size = int(self.size) if self.size else 0
                except (TypeError, ValueError):
                    type_size = 0
                return int(score_member(name, type_size))
        except (ImportError, AttributeError, TypeError, KeyError, NameError):
            pass
        try:
            if self.tinfo is not None and bool(self.tinfo.is_funcptr()):
                return 0x1000 + len(str(self.tinfo))
        except (AttributeError, RuntimeError):
            pass
        return 0xFFFF

    def type_equals_to(self, tinfo: Any) -> bool:
        """Default type-equality check — ``self.tinfo.equals_to(tinfo)``.

        Mirrors original ``AbstractMember.type_equals_to``
        (``core/temporary_structure.py:180-181``). ``VoidMember`` overrides
        this to always return True (wildcard).
        """
        if self.tinfo is None or tinfo is None:
            return False
        try:
            return bool(self.tinfo.equals_to(tinfo))
        except (AttributeError, RuntimeError):
            return False


@dataclass
class Member(AbstractMember):
    """A struct member with a known tinfo."""

    pass


@dataclass
class VoidMember(AbstractMember):
    """Fallback member when no tinfo can be inferred (byte/char).

    Original sets ``is_array=True`` and ``tinfo=BYTE_TINFO`` (or CHAR_TINFO)
    so that consecutive void members show as ``_BYTE[]`` / ``char[]``.
    """

    tinfo: Any = None
    name: str = "void"
    is_array: bool = True

    def __post_init__(self) -> None:
        # Ensure ``tinfo`` is always a real IDA tinfo — IDA's UDT API
        # rejects ``None`` with ValueError. Default to an unsigned byte
        # (``_BYTE``), matching the original VoidMember's behaviour.
        if self.tinfo is None:
            self.tinfo = _make_byte_tinfo()

    def type_equals_to(self, other_type: Any) -> bool:
        return True  # wildcard — always matches

    def switch_array_flag(self) -> None:
        # Void members stay as arrays (you can't "un-array" a byte).
        pass
