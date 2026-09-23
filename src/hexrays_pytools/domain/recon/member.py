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

# C keywords that can never be a struct member name — used by
# ``get_udt_member`` to avoid emitting invalid cdecl (e.g. ``_BYTE void;``).
_C_KEYWORDS: frozenset[str] = frozenset({
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "int", "long", "register", "return", "short", "signed", "sizeof",
    "static", "struct", "switch", "typedef", "union", "unsigned", "void",
    "volatile", "while", "bool", "true", "false",
})


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
    scanned_variables: set[Any] = field(default_factory=set)

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
        self.is_array = False

    def switch_array_flag(self) -> None:
        """Toggle ``is_array`` (VoidMember overrides to no-op)."""
        self.is_array = not self.is_array

    @property
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
        elif not self.name or not str(self.name).isidentifier() or str(self.name) in _C_KEYWORDS:
            # Bug fix (found by verification/verify_parity.py on IDA 9.4):
            # VoidMember's default name is ``void`` — a C keyword. Emitting
            # ``_BYTE void;`` into the pack cdecl makes IDA's parser reject
            # the whole struct ("Syntax error near: }"). The v1 plugin never
            # hit this because Member.__init__ always auto-named members
            # ``byte_<offset>``; our dataclass keeps the display name "void"
            # instead. Generate a positional name here the same way v1 did.
            operand = self.type_name.replace("[", "").replace("]", "").replace("*", "").strip()
            if not operand or not operand.isidentifier() or operand in _C_KEYWORDS:
                operand = "byte"
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
        # Reconstruction offsets/sizes are stored in bytes; IDA 9 UDT
        # members use bit offsets/sizes.
        udt_member.offset = (int(self.offset) - int(offset)) * 8
        element_count = int(array_size) if array_size else 1
        udt_member.size = int(self.size) * element_count * 8
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
        # Merge scanned_variables on match (original plugin behavior):
        # equality is based on offset + type, not size. Distinct candidate
        # types with the same width must remain separate rows for scoring.
        if self.offset == other.offset and self.type_name == other.type_name:
            self.scanned_variables |= other.scanned_variables
            return True
        return False

    def __hash__(self) -> int:
        return hash((self.offset, self.type_name))

    def __lt__(self, other: AbstractMember) -> bool:
        if int(self.offset) != int(other.offset):
            return int(self.offset) < int(other.offset)
        return str(self.type_name) < str(other.type_name)

    @property
    def score(self) -> int:
        """Likelihood this member is the right candidate for its offset.

        Higher = better. Used by ``StructureModel.resolve_types`` (which keeps
        the higher-scoring candidate on collision).

        Ranking (TRex-style behavior capture):
        1. function pointers — strongest typed evidence (``0x1000 + len``);
        2. named types via :func:`score_member` — size-ranked;
        3. underscore-prefixed types (``_QWORD``, ``_DWORD``, …) — width
           known but semantics unknown, penalized by ``score_member`` so any
           named evidence outranks them;
        4. ``0xFFFF`` only when the score cannot be computed at all.

        (The previous version returned ``0xFFFF`` for underscore types — the
        *worst* sentinel per its own docstring — while ``resolve_types``
        keeps the *higher* score, so ``_QWORD`` manufactured by the scanner's
        arithmetic fallthrough beat real typed evidence. Found by
        verification/trex_bench against TRex, USENIX Security 25.)
        """
        try:
            if self.tinfo is not None and bool(self.tinfo.is_funcptr()):
                return 0x1000 + len(str(self.tinfo))
        except (AttributeError, RuntimeError):
            pass
        name = self.type_name
        if name and isinstance(name, str):
            try:
                type_size = int(self.size) if self.size else 0
            except (TypeError, ValueError):
                type_size = 0
            try:
                from ...pure.scoring import score_member  # noqa: PLC0415

                score = int(score_member(name, type_size))
            except (ImportError, AttributeError, TypeError, KeyError, ValueError):
                return 0xFFFF
            if score < 0 and name.startswith("_"):
                # IDA primitives (`_DWORD`, `_QWORD`, …) are width-true
                # behavior captures, not auto-generated names — the '_' name
                # penalty must not rank them below sub-width named evidence
                # (e.g. a `char` write inside a dword load, TRex would union
                # them). Only unknown underscore TYPES stay penalized.
                try:
                    if self.tinfo is not None and bool(
                        self.tinfo.is_integral() or self.tinfo.is_floating()
                    ):
                        score += 0x1000
                except (AttributeError, RuntimeError):
                    pass
            return score
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

    def __post_init__(self) -> None:
        # Scanner offsets are relative to the scanned object. v1 stores
        # candidates at ``offset + origin`` so scans started from a subobject
        # land at the correct absolute structure offset.
        self.offset = int(self.offset) + int(self.origin)
        if self.name:
            return
        operand = "field"
        if self.tinfo is not None:
            try:
                size = int(self.tinfo.get_size())
                if bool(self.tinfo.is_floating()):
                    operand = {1: "byte", 2: "word", 4: "float", 8: "double", 16: "ddouble"}.get(
                        size, "field"
                    )
                elif bool(self.tinfo.is_integral()):
                    operand = {1: "byte", 2: "word", 4: "dword", 8: "qword", 10: "tword", 16: "dqword"}.get(
                        size, "field"
                    )
            except (AttributeError, RuntimeError, TypeError, ValueError):
                pass
        self.name = f"{operand}_{int(self.offset):x}"


@dataclass
class VoidMember(AbstractMember):
    """Fallback member when no tinfo can be inferred (byte/char).

    Original sets ``is_array=True`` and ``tinfo=BYTE_TINFO`` (or CHAR_TINFO)
    so that consecutive void members show as ``_BYTE[]`` / ``char[]``.
    """

    tinfo: Any = None
    name: str = ""
    is_array: bool = True

    def __post_init__(self) -> None:
        self.offset = int(self.offset) + int(self.origin)
        # Ensure ``tinfo`` is always a real IDA tinfo — IDA's UDT API
        # rejects ``None`` with ValueError. Default to an unsigned byte
        # (``_BYTE``), matching the original VoidMember's behaviour.
        if self.tinfo is None:
            self.tinfo = _make_byte_tinfo()
        if not self.name:
            self.name = f"byte_{int(self.offset):x}"

    def type_equals_to(self, other_type: Any) -> bool:
        return True  # wildcard — always matches

    def switch_array_flag(self) -> None:
        # Void members stay as arrays (you can't "un-array" a byte).
        pass

    def set_enabled(self, enable: bool) -> None:
        # v1 intentionally preserves the array flag for byte runs.
        self.enabled = bool(enable)

    @property
    def font(self) -> Any:
        try:
            from PySide6 import QtGui

            return QtGui.QFont("Consolas", 10, italic=True)
        except (ImportError, AttributeError, TypeError):
            return None
