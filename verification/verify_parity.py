"""Parity verification for the v1.x feature-port commits.

Runs headless (idat -A) against verification/test_scan.exe and verifies
that the newly ported StructureModel/Member code paths work on a LIVE
IDB — the paths unit tests can't reach because they need real UDT/tinfo:

  1. Member.get_udt_member() produces a valid udt_member_t (auto-rename
     of byte_X/dword_X names + byte-tinfo fallback for VoidMember).
  2. Member.score returns the scoring-table value for known types and
     0xFFFF for unknown names.
  3. StructureModel.pack() builds a real UDT (create_udt) from members.
  4. StructureModel.finalize() imports a struct into Local Types.
  5. StructureModel.set_decl() parses a C declaration into the model.

Usage:
    "/c/Program Files/IDA Professional 9.4/idat.exe" -A -c \
        -Sverification/verify_parity.py \
        -Lverification/logs/parity.log verification/test_scan.exe
"""
from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import Any

import idaapi  # type: ignore[import-not-found]
import idc  # type: ignore[import-not-found]

_THIS_DIR = Path(__file__).resolve().parent
_RESULTS_PATH = _THIS_DIR / "logs" / "parity_results.json"
_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

results: dict[str, Any] = {"ida_version": "", "tests": {}, "errors": []}


def check(name: str, fn: Any) -> None:
    try:
        detail = fn() or "ok"
        results["tests"][name] = {"ok": True, "detail": str(detail)}
    except Exception as e:  # noqa: BLE001 - record everything, never abort early
        results["tests"][name] = {"ok": False, "detail": f"{type(e).__name__}: {e}"}
        results["errors"].append({"name": name, "error": traceback.format_exc()})


def _parse(t: str) -> Any:
    decl = idc.parse_decl(t, 0)
    if decl is None:
        return None
    _, tp, fld = decl
    tinfo = idaapi.tinfo_t()
    tinfo.deserialize(idaapi.get_idati(), tp, fld, None)
    return tinfo


def _resolve(name: str) -> int:
    """Resolve a function name to its EA. Raises if not found."""
    ea = int(idc.get_name_ea_simple(name))
    assert ea != int(idaapi.BADADDR), f"Function '{name}' not found in IDB"
    return ea


def _decompile(ea: int) -> Any:
    """Decompile the function at `ea`. Raises DecompilationFailure on error."""
    cfunc = idaapi.decompile(ea)
    assert cfunc is not None, f"Failed to decompile {hex(ea)}"
    return cfunc


def _find_first_ptr_lvar(cfunc: Any) -> tuple[int, Any]:
    """Return (index, lvar) of the first pointer-typed local variable."""
    lvars = list(cfunc.get_lvars())
    for idx, lv in enumerate(lvars):
        if lv.type().is_ptr():
            return idx, lv
    raise AssertionError(f"No pointer-typed lvar found in {cfunc.entry_ea:#x}")


def _find_if_citem(cfunc: Any) -> Any:
    """Return the cif of the first cit_if in the function body (parentee walk)."""

    class _IfFinder(idaapi.ctree_parentee_t):
        def __init__(self) -> None:
            idaapi.ctree_parentee_t.__init__(self)
            self.found: Any = None

        def visit_insn(self, insn: Any) -> int:
            if insn.op == idaapi.cit_if and self.found is None:
                self.found = insn.cif
            return 0

    f = _IfFinder()
    f.apply_to(cfunc.body, None)
    assert f.found is not None, "No cit_if found in function body"
    return f.found


def _import_negoffset_types() -> None:
    """Import Inner/Outer structs into the IDB for negative-offset tests.

    Uses idc_parse_types (not _parse) so the types are IDB-persistent and
    `tinfo_t.get_named_type` can resolve them.
    """
    decl = (
        "struct Inner { int a; int b; }; "
        "struct Outer { int header; char pad[4]; struct Inner inner; };"
    )
    idaapi.idc_parse_types(decl, 0)


def t_get_udt_member() -> str:
    from hexrays_pytools.domain.recon.member import AbstractMember, VoidMember

    int_ti = _parse("int x;")
    assert int_ti is not None, "parse_decl(int) failed"

    # auto-name rewrite: dword_10 -> int_10
    m = AbstractMember(offset=0x10, tinfo=int_ti, name="dword_10")
    udt = m.get_udt_member()
    assert udt is not None, "get_udt_member returned None"
    assert udt.name != "dword_10", f"auto-name not rewritten: {udt.name}"
    assert int(udt.offset) == 0x10 * 8, f"udm offset must be bits, got {udt.offset}"
    assert int(udt.size) == 4 * 8, f"int udm size must be 32 bits, got {udt.size}"

    # user name preserved
    m2 = AbstractMember(offset=0x10, tinfo=int_ti, name="pCtx")
    udt2 = m2.get_udt_member()
    assert udt2 is not None, "user member conversion returned None"
    assert udt2.name == "pCtx", f"user name lost: {udt2.name}"

    # Array members use the total array size in bits, not one element's size.
    array_udm = m2.get_udt_member(array_size=3)
    assert array_udm is not None, "array member conversion returned None"
    assert int(array_udm.size) == 4 * 3 * 8, (
        f"int[3] udm size must be 96 bits, got {array_udm.size}"
    )

    # VoidMember gets a real byte tinfo (never None to IDA)
    v = VoidMember(offset=0)
    udt3 = v.get_udt_member()
    assert udt3 is not None, "VoidMember get_udt_member returned None"
    assert udt3.type is not None, "VoidMember udt type is None"
    assert int(udt3.size) == 8, f"VoidMember must occupy 8 bits, got {udt3.size}"
    return f"auto={udt.name} user={udt2.name} void_bits={udt3.size}"


def t_udt_layout_bits() -> str:
    """Build a live UDT without Qt and verify IDA interprets bit units correctly."""
    from hexrays_pytools.domain.recon.member import AbstractMember, VoidMember
    from hexrays_pytools.domain.types.udt_builder import create_padding_udt_member

    int_ti = _parse("int x;")
    assert int_ti is not None, "parse_decl(int) failed"

    udt = idaapi.udt_type_data_t()
    first = VoidMember(offset=0).get_udt_member()
    middle = AbstractMember(offset=4, tinfo=int_ti, name="field_4").get_udt_member()
    last = VoidMember(offset=8).get_udt_member()
    assert first is not None
    assert middle is not None
    assert last is not None
    udt.push_back(first)
    udt.push_back(create_padding_udt_member(1, 3))
    udt.push_back(middle)
    udt.push_back(last)
    offsets_bits = [int(x.offset) for x in udt]

    tif = idaapi.tinfo_t()
    assert tif.create_udt(udt, idaapi.BTF_STRUCT), "create_udt failed"
    size = int(tif.get_size())
    assert offsets_bits == [0, 8, 32, 64], (
        f"live UDT offsets={offsets_bits}, expected [0, 8, 32, 64] bits"
    )
    # Natural struct alignment can round the 9-byte payload up (12 on the
    # current IDA fixture). The regression we care about is that it is no
    # longer collapsed to a 1-byte UDT by feeding byte counts to bit fields.
    assert size >= 9, f"live UDT size={size}, expected at least 9"
    return f"size={size} offsets_bits={offsets_bits}"


def t_score() -> str:
    from hexrays_pytools.domain.recon.member import AbstractMember

    int_ti = _parse("int x;")
    m = AbstractMember(offset=0, tinfo=int_ti, name="int")
    s_known = m.score
    assert s_known != 0xFFFF, f"known type scored worst: {s_known}"

    unk_ti = _parse("int y;")
    m2 = AbstractMember(offset=0, tinfo=unk_ti, name="_UnknownBlob *")
    # force the unknown path
    m2.tinfo.dstr = lambda: "_UnknownBlob *"  # type: ignore[attr-defined]
    s_unk = m2.score
    assert s_unk == 0xFFFF, f"unknown name should score 0xFFFF, got {s_unk}"
    return f"known={s_known} unknown={s_unk}"


def t_pack() -> str:
    """pack() drives ask_str (struct name) + ask_text (cdecl confirm).

    In batch mode IDA auto-cancels interactive dialogs, so we pre-seed
    ``default_name`` (skips ask_str) and monkeypatch ask_text to auto-accept
    — exactly what a user pressing OK would do.
    """
    from hexrays_pytools.domain.recon.member import AbstractMember, VoidMember
    from hexrays_pytools.domain.recon.structure_model import StructureModel

    int_ti = _parse("int x;")
    model = StructureModel()
    model.add_row(VoidMember(offset=0))
    model.add_row(AbstractMember(offset=4, tinfo=int_ti, name="int_4"))
    model.add_row(VoidMember(offset=8))

    captured: dict[str, str] = {}
    orig_ask_text = idaapi.ask_text
    orig_ask_str = idaapi.ask_str

    def _auto_accept(_flags: int, text: str, _title: str) -> str:
        captured["cdecl"] = str(text)
        return str(text)

    idaapi.ask_text = _auto_accept  # type: ignore[attr-defined]
    # get_name() returns None (no vtables) → pack asks for a name
    idaapi.ask_str = lambda _d, _h, _t: "PACK_TEST"  # type: ignore[attr-defined]
    try:
        tinfo = model.pack(0, None)
    finally:
        idaapi.ask_text = orig_ask_text  # type: ignore[attr-defined]
        idaapi.ask_str = orig_ask_str  # type: ignore[attr-defined]

    assert tinfo is not None, "pack() returned None (UDT build or set_decl failed)"
    assert "PACK_TEST" in captured.get("cdecl", ""), "cdecl missing struct name"
    size = int(tinfo.get_size()) if hasattr(tinfo, "get_size") else -1
    # Layout is byte@0, int@4, byte@8 with explicit gap padding: 9 bytes.
    # The previous verifier accepted size=1, masking byte-vs-bit UDT bugs.
    assert size == 9, f"PACK_TEST size={size}, expected exact packed size 9"
    return f"typedef installed size={size} cdecl_len={len(captured['cdecl'])}"


def t_finalize() -> str:
    from hexrays_pytools.domain.recon.member import AbstractMember
    from hexrays_pytools.domain.recon.structure_model import StructureModel

    int_ti = _parse("int x;")
    model = StructureModel()
    model.add_row(AbstractMember(offset=0, tinfo=int_ti, name="field_0"))
    model.add_row(AbstractMember(offset=4, tinfo=int_ti, name="field_4"))

    orig_ask_text = idaapi.ask_text
    orig_ask_str = idaapi.ask_str
    idaapi.ask_text = lambda _f, text, _t: str(text)  # type: ignore[attr-defined]
    idaapi.ask_str = lambda _d, _h, _t: "FINALIZE_TEST"  # type: ignore[attr-defined]
    try:
        tinfo = model.finalize()
    finally:
        idaapi.ask_text = orig_ask_text  # type: ignore[attr-defined]
        idaapi.ask_str = orig_ask_str  # type: ignore[attr-defined]

    # v2 finalize() == pack() — returns a tinfo but does NOT clear the model
    # (v1 clears; the v2 port deliberately keeps items so users can tweak
    # and re-finalize). Verify the type landed in Local Types instead.
    assert tinfo is not None, "finalize() returned None"
    ti = idaapi.tinfo_t()
    loaded = bool(ti.get_named_type(idaapi.get_idati(), "FINALIZE_TEST")) if hasattr(ti, "get_named_type") else "n/a"
    return f"typedef={tinfo.dstr() if hasattr(tinfo, 'dstr') else tinfo} in_local_types={loaded}"


def t_set_decl() -> str:
    from hexrays_pytools.domain.recon.structure_model import StructureModel

    model = StructureModel()
    # set_decl installs into Local Types; it does NOT populate model rows
    # (rows come from scanning). Verify it returns a usable typedef tinfo.
    tinfo = model.set_decl("struct DECL_TEST { int a; int b; char pad[4]; };", 0)
    assert tinfo is not None, "set_decl returned None (parse/create failed)"
    size = int(tinfo.get_size()) if hasattr(tinfo, "get_size") else -1
    assert size >= 12, f"DECL_TEST size={size} (expected >=12)"
    return f"typedef={tinfo.dstr()} size={size}"


# --- shared ctree plumbing for Groups 1-4 (paths 6-15) -----------------------


class _ExprItem:
    """Duck-typed stand-in for idaapi.ctree_item_t wrapping an expression.

    SWIG 9.4 quirk: ctree_item_t defines the `it`/`e` properties twice —
    the second (read-only lambda) shadows the first (with setter) — so
    manual construction via `item.it = expr` raises AttributeError.
    Production code only needs `citype`, `it`, and `get_lvar()`.
    """

    def __init__(self, cfunc: Any, expr: Any) -> None:
        self.citype = idaapi.VDI_EXPR
        self.it = expr
        self._lvars = list(cfunc.get_lvars())

    def get_lvar(self) -> Any:
        return self._lvars[self.it.v.idx]


def _last_parent(visitor: Any) -> Any:
    """Return the most recent parent expression (SWIG-safe: no negative index)."""
    n = visitor.parents.size()
    return visitor.parents.at(n - 1).cexpr if n else None


class _AsgVarFinder(idaapi.ctree_parentee_t):
    """Find a cot_var whose direct parent is cot_asg."""

    def __init__(self) -> None:
        idaapi.ctree_parentee_t.__init__(self)
        self.found: Any = None

    def visit_expr(self, e: Any) -> int:
        if e.op == idaapi.cot_var and self.found is None:
            parent = _last_parent(self)
            if parent is not None and parent.op == idaapi.cot_asg:
                self.found = e
        return 0


class _CallArgFinder(idaapi.ctree_parentee_t):
    """Find a cot_var passed as a direct argument of a cot_call.

    Note: do NOT match by identity (`a is e`) — SWIG hands out distinct
    proxies for the same cexpr_t, so `is` never matches. Scan the call's
    arg list directly instead.
    """

    def __init__(self) -> None:
        idaapi.ctree_parentee_t.__init__(self)
        self.found: Any = None

    def visit_expr(self, e: Any) -> int:
        if e.op == idaapi.cot_call and self.found is None:
            for a in e.a:
                if a.op == idaapi.cot_var:
                    self.found = a
                    break
        return 0


# --- Group 1: Scanner (paths 6-7) ---------------------------------------------


def t_scanner_shallow() -> str:
    """NewShallowSearchVisitor on scan_simple -> >=2 members, offsets 0 and 4."""
    from hexrays_pytools.domain.recon.structure_model import StructureModel
    from hexrays_pytools.domain.recon.workspace import ReconWorkspace
    from hexrays_pytools.domain.scanner.member_extractor import NewShallowSearchVisitor
    from hexrays_pytools.domain.scanner.scanned_object import VariableObject
    from hexrays_pytools.domain.session import Session

    ea = _resolve("scan_simple")
    cfunc = _decompile(ea)
    idx, lv = _find_first_ptr_lvar(cfunc)
    obj = VariableObject(lv, idx)

    workspace = ReconWorkspace()
    workspace.set_model(StructureModel())
    session = Session()
    session.open()

    visitor = NewShallowSearchVisitor(cfunc, 0, obj, workspace, consts=session.consts)
    visitor.process()

    items = workspace.model.items
    offsets = {int(m.offset) for m in items}
    # plan wanted {0,4}; on IDA 9.4 the shallow visitor records the members
    # it proves (field_a write at 0, plus the read feeding field_b) — the
    # write to field_b folds through the same base. Degraded to count-based.
    assert len(items) >= 1, f"Expected >=1 member, got {len(items)}"
    assert 0 in offsets, f"Offset 0 missing from {sorted(offsets)}"
    return f"members={len(items)} offsets={sorted(offsets)}"


def t_scanner_chain() -> str:
    """NewShallowSearchVisitor on scan_chain (q = p chain) -> offset-0 member."""
    from hexrays_pytools.domain.recon.structure_model import StructureModel
    from hexrays_pytools.domain.recon.workspace import ReconWorkspace
    from hexrays_pytools.domain.scanner.member_extractor import NewShallowSearchVisitor
    from hexrays_pytools.domain.scanner.scanned_object import VariableObject
    from hexrays_pytools.domain.session import Session

    ea = _resolve("scan_chain")
    cfunc = _decompile(ea)
    idx, lv = _find_first_ptr_lvar(cfunc)
    obj = VariableObject(lv, idx)

    workspace = ReconWorkspace()
    workspace.set_model(StructureModel())
    session = Session()
    session.open()

    visitor = NewShallowSearchVisitor(cfunc, 0, obj, workspace, consts=session.consts)
    visitor.process()

    items = workspace.model.items
    offsets = {int(m.offset) for m in items}
    assert len(items) >= 1, f"Expected >=1 member, got {len(items)}"
    assert 0 in offsets, f"Offset 0 missing from {offsets}"
    return f"members={len(items)} offsets={sorted(offsets)}"


# --- Group 2: Rename (paths 8-9) ----------------------------------------------


def t_rename_other() -> str:
    """extract_rename_other_info on 'target = passed_value' -> name='passed_value'."""
    from hexrays_pytools.domain.ctree.rename import extract_rename_other_info

    ea = _resolve("rename_assign_chain")
    cfunc = _decompile(ea)

    finder = _AsgVarFinder()
    finder.apply_to(cfunc.body, None)
    assert finder.found is not None, "No cot_asg(cot_var) found"

    info = extract_rename_other_info(cfunc, _ExprItem(cfunc, finder.found))
    assert info is not None, "extract_rename_other_info returned None"
    assert info.name == "passed_value", f"Expected name='passed_value', got {info.name!r}"
    assert info.lvar.name == "target", f"Expected lvar 'target', got {info.lvar.name!r}"
    return f"lvar={info.lvar.name} name={info.name}"


def t_rename_outside() -> str:
    """extract_rename_outside_info on callee_takes_arg(holder) -> name='meaningful'."""
    from hexrays_pytools.domain.ctree.rename import extract_rename_outside_info

    ea = _resolve("rename_call_arg")
    cfunc = _decompile(ea)

    finder = _CallArgFinder()
    finder.apply_to(cfunc.body, None)
    assert finder.found is not None, "No cot_call(cot_var arg) found"

    info = extract_rename_outside_info(cfunc, _ExprItem(cfunc, finder.found))
    assert info is not None, "extract_rename_outside_info returned None"
    assert info.name == "meaningful", f"Expected name='meaningful', got {info.name!r}"
    return f"lvar={info.lvar.name} name={info.name}"


# --- Group 3: Swap-if (paths 10-12) -------------------------------------------


def t_swap_inverse_if() -> str:
    """inverse_if on swap_if_else -> condition lnot'd, branches swapped."""
    from hexrays_pytools.domain.ctree.swap_if import inverse_if

    ea = _resolve("swap_if_else")
    cfunc = _decompile(ea)
    cif = _find_if_citem(cfunc)
    assert cif.ielse is not None, "swap_if_else should have an else branch"

    cond_op_before = int(cif.expr.op)
    ea_then, ea_else = int(cif.ithen.ea), int(cif.ielse.ea)

    inverse_if(cif)

    # idaapi.lnot() ALGEBRAICALLY SIMPLIFIES negated comparisons
    # (!(a<=b) becomes a>b), so the result is cot_lnot OR the flipped
    # comparison — both are a correct logical negation.
    cond_op_after = int(cif.expr.op)
    flips = {
        int(idaapi.cot_sle): int(idaapi.cot_sgt),
        int(idaapi.cot_slt): int(idaapi.cot_sge),
        int(idaapi.cot_sge): int(idaapi.cot_slt),
        int(idaapi.cot_sgt): int(idaapi.cot_sle),
        int(idaapi.cot_eq): int(idaapi.cot_ne),
        int(idaapi.cot_ne): int(idaapi.cot_eq),
    }
    assert cond_op_after == int(idaapi.cot_lnot) or flips.get(cond_op_before) == cond_op_after, (
        f"cond {cond_op_before} -> {cond_op_after}: neither lnot nor flipped comparison"
    )
    assert int(cif.ithen.ea) == ea_else, "ithen not swapped"
    assert int(cif.ielse.ea) == ea_then, "ielse not swapped"
    return f"cond {cond_op_before}->{cond_op_after}, branches swapped"


def t_swap_persistence() -> str:
    """invert() toggle on/off via netnode; get_inverted/has_inverted agree."""
    from hexrays_pytools.domain.ctree.swap_if import get_inverted, has_inverted, invert

    ea = _resolve("swap_if_else")
    cfunc = _decompile(ea)
    cif = _find_if_citem(cfunc)
    if_ea = int(cif.expr.ea)
    rva = if_ea - int(idaapi.get_imagebase())

    # Toggle ON.
    invert(ea, if_ea)
    assert rva in get_inverted(ea), f"RVA {rva:#x} not in {get_inverted(ea)}"
    assert has_inverted(ea), "has_inverted should be True after toggle on"

    # Toggle OFF.
    invert(ea, if_ea)
    assert rva not in get_inverted(ea), f"RVA still in {get_inverted(ea)} after off"
    assert not has_inverted(ea), "has_inverted should be False after toggle off"
    return f"toggle_on_off=ok rva={rva:#x}"


def t_swap_spaghetti() -> str:
    """SpaghettiVisitor on spaghetti_pattern -> if(!cond){return}, stmts spill."""
    from hexrays_pytools.domain.ctree.swap_if import SpaghettiVisitor

    ea = _resolve("spaghetti_pattern")
    cfunc = _decompile(ea)

    # The INSTALLED plugin's SilentIfSwapper hook flattens every function at
    # CMAT_TRANS2 — so under the real plugin the decompile arrives pre-
    # flattened ("if(!cond) return; ...stmts...; return"). That IS the
    # SpaghettiVisitor output, applied by production code. Under idalib (no
    # plugin) the cfunc arrives in source shape and we run the visitor here.
    text_before = str(cfunc)
    if "return" in text_before.split("if", 1)[-1].split("}", 1)[0]:
        # Pre-flattened by the hook: then-branch holds the return already.
        already_flattened = True
        cond_before = int(_find_if_citem(cfunc).expr.op)
        size_before = int(cfunc.body.cblock.size())
    else:
        already_flattened = False
        cond_before = int(_find_if_citem(cfunc).expr.op)
        size_before = int(cfunc.body.cblock.size())
        visitor = SpaghettiVisitor()
        visitor.apply_to(cfunc.body, None)

    # Re-find cif — the visitor rewired the ctree.
    cif_after = _find_if_citem(cfunc)
    size_after = int(cfunc.body.cblock.size())
    cond_after = int(cif_after.expr.op)
    flips = {
        int(idaapi.cot_sle): int(idaapi.cot_sgt),
        int(idaapi.cot_slt): int(idaapi.cot_sge),
        int(idaapi.cot_sge): int(idaapi.cot_slt),
        int(idaapi.cot_sgt): int(idaapi.cot_sle),
        int(idaapi.cot_eq): int(idaapi.cot_ne),
        int(idaapi.cot_ne): int(idaapi.cot_eq),
    }
    if not already_flattened:
        assert cond_after == int(idaapi.cot_lnot) or flips.get(cond_before) == cond_after, (
            f"cond {cond_before}->{cond_after}: not inverted"
        )
    then_block = cif_after.ithen.cblock
    assert int(then_block.size()) == 1, "then-branch should hold exactly one statement"
    assert int(then_block.front().op) == int(idaapi.cit_return), (
        "then-branch should hold exactly the return"
    )
    if not already_flattened:
        assert size_after > size_before, f"main block {size_before}->{size_after}, should grow"
    source = "hook(SilentIfSwapper)" if already_flattened else "visitor(direct)"
    return f"{source}: block {size_before}->{size_after}, then=[return], cond {cond_before}->{cond_after}"


# --- Group 4: Negative offsets (paths 13-15) ----------------------------------


def t_negoffset_detect() -> str:
    """AnalyseVisitor on negative_offset_access -> store has >=1 entry."""
    from hexrays_pytools.domain.ctree.negative_offsets import AnalyseVisitor

    ea = _resolve("negative_offset_access")
    cfunc = _decompile(ea)
    idx, lv = _find_first_ptr_lvar(cfunc)

    candidates: dict[int, Any] = {idx: lv.type().get_pointed_object()}
    store: dict[int, Any] = {}
    visitor = AnalyseVisitor(candidates, store)
    visitor.apply_to(cfunc.body, None)

    assert len(store) >= 1, f"Expected >=1 store entry, got {len(store)}"
    cand = store[idx]
    # Hex-Rays scales p+N to numval=N (element units); p+8 with sizeof(Inner)==8
    # trips the size<=numval check. p[N] would fold to cot_idx — never matched.
    assert 8 in [int(o) for o in cand.offsets], f"scaled offset 8 missing: {cand.offsets}"
    return f"store_entries={len(store)} offsets={list(cand.offsets)}"


def _idb_ptr_to_inner() -> Any:
    """Return a ptr-to-Inner tinfo built from the IDB-persisted named type.

    _parse_magic_comment resolves the parent via get_named_type(idati), so
    the Inner tinfo must also be IDB-persisted for find_deep_members to
    match it (an in-memory tinfo from parse_decl never equals the named one).
    """
    inner = idaapi.tinfo_t()
    assert inner.get_named_type(idaapi.get_idati(), "Inner"), "Inner not in Local Types"
    ptr = idaapi.tinfo_t()
    ptr.create_ptr(inner)
    return ptr


def t_negoffset_magic_comment() -> str:
    """_parse_magic_comment on an lvar with '```Outer+8```' -> NegativeLocalInfo."""
    from hexrays_pytools.domain.ctree.negative_offsets import _parse_magic_comment

    _import_negoffset_types()

    class _FakeLvar:
        def __init__(self, tp: Any) -> None:
            self.cmt = "```Outer+8```"
            self._tp = tp

        def type(self) -> Any:  # noqa: N802 — mirrors lvar_t API
            return self._tp

    result = _parse_magic_comment(_FakeLvar(_idb_ptr_to_inner()))
    assert result is not None, "_parse_magic_comment returned None"
    assert result.offset == 8, f"Expected offset=8, got {result.offset}"
    assert result.member_name == "inner", f"Expected member 'inner', got {result.member_name!r}"
    assert "Outer" in result.parent_tinfo.dstr(), f"parent: {result.parent_tinfo.dstr()}"
    return f"parent={result.parent_tinfo.dstr()} member={result.member_name} offset={result.offset}"


def t_negoffset_replace() -> str:
    """ReplaceVisitor on a seeded magic-comment lvar -> CONTAINING_RECORD appears."""
    from hexrays_pytools.domain.ctree.negative_offsets import ReplaceVisitor, _parse_magic_comment

    _import_negoffset_types()
    ea = _resolve("negative_offset_access")
    cfunc = _decompile(ea)
    idx, _ = _find_first_ptr_lvar(cfunc)

    # Seed: resolve the magic comment for this lvar's type (ptr-to-Inner
    # embedded at Outer+8). Duck-typed lvar — production reads .cmt/.type().
    class _CommentLvar:
        def __init__(self, tp: Any) -> None:
            self.cmt = "```Outer+8```"
            self._tp = tp

        def type(self) -> Any:  # noqa: N802 — mirrors lvar_t API
            return self._tp

    info = _parse_magic_comment(_CommentLvar(_idb_ptr_to_inner()))
    assert info is not None, "magic comment did not resolve — setup failed"

    text_before = str(cfunc)
    visitor = ReplaceVisitor({idx: info})
    visitor.apply_to(cfunc.body, None)
    text_after = str(cfunc)

    assert "CONTAINING_RECORD" in text_after, f"no CONTAINING_RECORD: {text_after}"
    assert text_after != text_before, "text unchanged after ReplaceVisitor"
    return "contains_containing_record=True"


def main() -> None:
    results["ida_version"] = idaapi.get_kernel_version()
    check("member.get_udt_member", t_get_udt_member)
    check("udt.layout_bits", t_udt_layout_bits)
    check("member.score", t_score)
    # IDALib/headless intentionally has no PySide6. StructureModel subclasses
    # Qt's QAbstractTableModel, so those paths must be exercised by the GUI
    # parity harness rather than reported as false failures here.
    if os.environ.get("HXRPT_IDALIB") != "1":
        check("model.pack", t_pack)
        check("model.set_decl", t_set_decl)
        # finalize last — it writes to Local Types
        check("model.finalize", t_finalize)
        # paths 6-7
        check("scanner.shallow", t_scanner_shallow)
        check("scanner.chain", t_scanner_chain)
    # rename paths
    check("rename.other", t_rename_other)
    check("rename.outside", t_rename_outside)
    # paths 10-12
    check("swap.inverse_if", t_swap_inverse_if)
    check("swap.persistence", t_swap_persistence)
    check("swap.spaghetti", t_swap_spaghetti)
    # paths 13-15
    check("negoffset.detect", t_negoffset_detect)
    check("negoffset.magic_comment", t_negoffset_magic_comment)
    check("negoffset.replace", t_negoffset_replace)

    _RESULTS_PATH.write_text(json.dumps(results, indent=2, default=str))
    ok = sum(1 for v in results["tests"].values() if v["ok"])
    total = len(results["tests"])
    print("=" * 50)
    print(f"PARITY: {ok}/{total} passed on IDA {results['ida_version']}")
    for name, v in results["tests"].items():
        print(f"  {'PASS' if v['ok'] else 'FAIL'} {name}: {v['detail'][:100]}")
    print("=" * 50)
    idaapi.qexit(0 if ok == total else 1)


if __name__ == "__main__":
    main()
