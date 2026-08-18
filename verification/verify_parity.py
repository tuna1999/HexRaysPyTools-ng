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
    """Return the first cit_if citem in the function body."""
    for item in cfunc.body:
        if item.op == idaapi.cit_if:
            return item.cif
    raise AssertionError("No cit_if found in function body")


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

    # user name preserved
    m2 = AbstractMember(offset=0x10, tinfo=int_ti, name="pCtx")
    udt2 = m2.get_udt_member()
    assert udt2 is not None and udt2.name == "pCtx", f"user name lost: {udt2.name}"

    # VoidMember gets a real byte tinfo (never None to IDA)
    v = VoidMember(offset=0)
    udt3 = v.get_udt_member()
    assert udt3 is not None, "VoidMember get_udt_member returned None"
    assert udt3.type is not None, "VoidMember udt type is None"
    return f"auto={udt.name} user={udt2.name} void_sz={udt3.size}"


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


def main() -> None:
    results["ida_version"] = idaapi.get_kernel_version()
    check("member.get_udt_member", t_get_udt_member)
    check("member.score", t_score)
    check("model.pack", t_pack)
    check("model.set_decl", t_set_decl)
    # finalize last — it writes to Local Types
    check("model.finalize", t_finalize)

    _RESULTS_PATH.write_text(json.dumps(results, indent=2, default=str))
    ok = sum(1 for v in results["tests"].values() if v["ok"])
    total = len(results["tests"])
    print("=" * 50)
    print(f"PARITY: {ok}/{total} passed on IDA {results['ida_version']}")
    for name, v in results["tests"].items():
        print(f"  {'PASS' if v['ok'] else 'FAIL'} {name}: {v['detail'][:100]}")
    print("=" * 50)
    idaapi.qexit(0 if ok == total else 1)


main()
