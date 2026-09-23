"""Headless scanner benchmark for HexRaysPyTools-ng (run via `idat -S`).

Scans the first pointer argument of each `bench_*` function with the
project's scanner (NewShallowSearchVisitor), runs resolve_types(), and dumps
the RAW member evidence to JSON (path from env TREX_BENCH_OUT). Scoring
against ground truth happens outside IDA in score_trex_bench.py so that
scoring-logic changes never require re-running IDA.

Deterministic: same binary + same IDA version + fresh database (-c) always
produces the same decompilation and the same member set.
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))

import ida_auto  # type: ignore[import-not-found]  # noqa: E402
import idaapi  # type: ignore[import-not-found]  # noqa: E402
import idc  # type: ignore[import-not-found]  # noqa: E402

# Ground-truth struct types imported into the IDB before any decompile so the
# decompiler sees known struct names (rather than anonymous equivalents) and
# scanner-collected struct references resolve through `get_named_type`.
# Mirrors `_import_negoffset_types` in verify_parity.py — using
# `idc_parse_types` (not `_parse`) makes them IDB-persistent.
_LOCAL_TYPES_DECL = (
    "struct Simple { int a; int b; long long c; }; "
    "struct Inner { int x; int y; }; "
    "struct Nested { int tag; struct Inner in; }; "
    "struct List { int data; struct List *next; }; "
    "struct WithArr { int prefix; int items[8]; }; "
    "struct MultiW { unsigned int whole; unsigned int after; }; "
    "struct Funcy { int id; int (*cb)(int); void *ctx; }; "
    "struct Shapes { char tag; long long val; }; "
    "struct Shared { int a; char *name; long long v; }; "
    "struct Unit { int x; int y; }; "
    "struct HasUnit { int tag; struct Unit u; }; "
    "struct List0 { struct List0 *next; int data; }; "
    "union Mix { unsigned int u32; unsigned char b[4]; };"
    "struct NegInner { int x; };"
    "struct NegOuter { int tag; struct NegInner inner; };"
)


def _install_local_types() -> None:
    """Inject the bench struct types into Local Types (idempotent).

    Lets the decompiler and scanner see known struct names rather than
    anonymous equivalents so ``get_named_type`` resolves them and the
    decompiler's propagated member references land in named structs.
    Best-effort: any parsing error is silently ignored so the harness
    still runs even if a particular Local Types slot is unavailable.
    """
    with contextlib.suppress(Exception):
        idaapi.idc_parse_types(_LOCAL_TYPES_DECL, 0)


# struct name -> functions that touch it + ground-truth fields (offset, size)
# in bytes for x86-64. Keep in sync with verification/trex_bench.c.
BENCH: dict[str, dict[str, Any]] = {
    "Simple": {"funcs": ["bench_simple"], "fields": [[0, 4], [4, 4], [8, 8]]},
    "Nested": {"funcs": ["bench_nested"], "fields": [[0, 4], [4, 8]]},
    "List": {"funcs": ["bench_list_walk"], "fields": [[0, 4], [8, 8]]},
    "WithArr": {"funcs": ["bench_array_sum", "bench_array_static"], "fields": [[0, 4], [4, 32]]},
    "MultiW": {"funcs": ["bench_multi_wide", "bench_multi_narrow"], "fields": [[0, 4], [4, 4]]},
    "Funcy": {"funcs": ["bench_funcy"], "fields": [[0, 4], [8, 8], [16, 8]]},
    "Shapes": {"funcs": ["bench_shapes"], "fields": [[0, 1], [8, 8]]},
}

# Segment 2 additions. "visitor": "deep" scans with NewDeepSearchVisitor
# (recurses into callees) — the interprocedural workflow.
BENCH.update(
    {
        "Shared": {
            "funcs": ["bench_interproc"],
            "fields": [[0, 4], [8, 8], [16, 8]],
            "visitor": "deep",
        },
        "HasUnit": {
            "funcs": ["bench_unit"],
            "fields": [[0, 4], [4, 8]],
            "visitor": "deep",
        },
        "List0": {"funcs": ["bench_list0"], "fields": [[0, 8], [8, 4]]},
        "Mix": {"funcs": ["bench_mix_wide", "bench_mix_narrow"], "fields": [[0, 4]]},
    }
)

# Segment 3 — negative-offset (CONTAINING_RECORD, paper §3.3.4 sub-object).
# Workflow: scan a struct-pointer lvar once, programmatically apply a
# magic comment naming a containing struct + member, then run
# ``collect_potential_negatives`` to rewrite the ctree with
# ``CONTAINING_RECORD(...)`` and re-scan to recover the containing field.
BENCH_NEGATIVE_OFFSETS: dict[str, dict[str, Any]] = {
    "NegOuter": {
        "funcs": ["neg_offset_access"],
        # tag@0 (Outer), inner.x@0 (Inner), tag+offset together occupy
        # absolute offsets 0 (Outer.tag) and 4 (Inner within Outer)... but
        # we measure what the scanner can recover from a SINGLE lvar's
        # CONTAINING_RECORD application — only NegOuter's tag (@0) is the
        # containing access; the inner.x is a regular inner access (@0).
        # Score it against gt [[0, 4]] (Outer.tag) and [[0, 4]] (Inner.x)
        # are the same offset — measurement target is the containing tag.
        "fields": [[0, 4]],
        "magic_comment": "```NegOuter+0```",
    },
}


def _apply_magic_comment(lvar: Any, cfunc: Any, comment: str) -> bool:
    """Set the lvar's user comment to apply a CONTAINING_RECORD hint.

    Returns True if the comment was applied (false on API mismatch —
    ``set_user_lvar_comment`` is not available on every IDA build).
    """
    try:
        ea = int(cfunc.entry_ea)
        if hasattr(lvar, "set_user_lvar_comment"):
            lvar.set_user_lvar_comment(ea, comment)
            return True
        # Fallback: set lvar.cmt attribute directly (some bindings expose it).
        lvar.cmt = comment
        return True
    except Exception:
        return False


def _apply_containing_record(cfunc: Any, lvar_idx: int, comment: str) -> bool:
    """Apply the magic comment + run negative_offsets.collect_potential_negatives.

    Returns True if the rewrite succeeded and the ctree now contains
    a CONTAINING_RECORD helper call.
    """
    from hexrays_pytools.domain.ctree.negative_offsets import (
        collect_potential_negatives,
    )

    lvars = list(cfunc.get_lvars())
    if lvar_idx >= len(lvars):
        return False
    lvar = lvars[lvar_idx]
    if not _apply_magic_comment(lvar, cfunc, comment):
        return False
    try:
        collect_potential_negatives(cfunc, {})
    except Exception:
        return False
    return any(
        getattr(ce, "op", None) is not None
        and int(getattr(ce, "op", -1)) == idaapi.cot_helper
        and getattr(ce, "helper", None) == "CONTAINING_RECORD"
        for ce in _iter_all_cexprs(cfunc.body)
    )


def _iter_all_cexprs(item: Any) -> Any:
    """Yield every cexpr under a ctree item (best-effort traversal)."""
    stack = [item]
    while stack:
        cur = stack.pop()
        if cur is None:
            continue
        yield cur
        op = getattr(cur, "op", None)
        if op is None:
            continue
        # cexprs: x, y; citems: expr, details
        for attr in ("x", "y", "a", "expr"):
            sub = getattr(cur, attr, None)
            if sub is not None and getattr(sub, "op", None) is not None:
                stack.append(sub)
        if int(op) == idaapi.cit_expr:
            stack.append(getattr(cur, "cexpr", None))
        if int(op) == idaapi.cit_if:
            for attr in ("ithen", "ielse"):
                stack.append(getattr(cur, attr, None))


def _scan_neg_offset(
    fn: str,
    var_idx: int,
    magic_comment: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Scan + optionally run CONTAINING_RECORD rewrite.

    Returns (members, errors). Members come from BOTH the original ctree
    AND the CONTAINING_RECORD-rewritten ctree (whichever produced
    evidence); ``resolve_types`` is run on the union.
    """
    from hexrays_pytools.domain.recon.structure_model import StructureModel
    from hexrays_pytools.domain.recon.workspace import ReconWorkspace
    from hexrays_pytools.domain.scanner.member_extractor import NewShallowSearchVisitor
    from hexrays_pytools.domain.scanner.scanned_object import VariableObject
    from hexrays_pytools.domain.session import Session

    errs: list[str] = []
    cfunc1 = _decompile(_resolve(fn))
    workspace = ReconWorkspace()
    workspace.set_model(StructureModel())
    session = Session()
    session.open()
    try:
        lvars1 = list(cfunc1.get_lvars())
        NewShallowSearchVisitor(
            cfunc1, 0, VariableObject(lvars1[var_idx], var_idx), workspace, consts=session.consts
        ).process()
    except Exception as e:
        errs.append(f"scan1: {e!r}")

    # Run CONTAINING_RECORD workflow: magic comment → collect_potential_negatives.
    ok = _apply_containing_record(cfunc1, var_idx, magic_comment)
    if ok:
        # Refresh the cfunc — ctree was rewritten in place.
        cfunc2 = _decompile(_resolve(fn))
        try:
            lvars2 = list(cfunc2.get_lvars())
            NewShallowSearchVisitor(
                cfunc2, 0, VariableObject(lvars2[var_idx], var_idx), workspace, consts=session.consts
            ).process()
        except Exception as e:
            errs.append(f"scan2: {e!r}")

    try:
        workspace.model.resolve_types()
    except Exception as e:
        errs.append(f"resolve: {e!r}")
    members = []
    for m in workspace.model.items:
        members.append(
            {
                "offset": int(m.offset),
                "size": int(m.size),
                "type_name": str(m.type_name),
                "enabled": bool(m.enabled),
                "is_array": bool(m.is_array),
                "score": int(m.score),
            }
        )
    session.close()
    return members, errs

def _resolve(name: str) -> int:
    ea = int(idc.get_name_ea_simple(name))
    if ea == idc.BADADDR:
        raise AssertionError(f"symbol not found: {name}")
    return ea


def _decompile(ea: int) -> Any:
    cfunc = idaapi.decompile(ea)
    if cfunc is None:
        raise AssertionError(f"decompile failed at {ea:#x}")
    return cfunc


def _first_ptr_lvar(cfunc: Any) -> tuple[int, Any]:
    """First pointer lvar, or None (caller may force a pointer type)."""
    for idx, lv in enumerate(cfunc.get_lvars()):
        try:
            tinfo: Any = lv.type() if callable(lv.type) else lv.type
            if bool(tinfo.is_ptr()):
                return idx, lv
        except (AttributeError, RuntimeError):
            continue
    return -1, None


def _prepare_scan(fn: str) -> tuple[Any, int, Any]:
    """Decompile `fn` and return (cfunc, lvar_idx, lvar) of its first argument.

    No type forcing: the benchmark measures the scanner on whatever Hex-Rays
    inferred on a fresh database (matching a user's first-scan experience).
    """
    cfunc = _decompile(_resolve(fn))
    lvars = list(cfunc.get_lvars())
    if not lvars:
        raise AssertionError(f"{fn}: no lvars")
    return cfunc, 0, lvars[0]


def run() -> list[dict[str, Any]]:
    from hexrays_pytools.domain.recon.structure_model import StructureModel
    from hexrays_pytools.domain.recon.workspace import ReconWorkspace

    _install_local_types()
    from hexrays_pytools.domain.scanner.member_extractor import (
        NewDeepSearchVisitor,
        NewShallowSearchVisitor,
    )
    from hexrays_pytools.domain.scanner.scanned_object import VariableObject
    from hexrays_pytools.domain.session import Session

    session = Session()
    session.open()
    results: list[dict[str, Any]] = []
    try:
        for struct_name, spec in BENCH.items():
            entry: dict[str, Any] = {
                "struct": struct_name,
                "fields": spec["fields"],
                "members": [],
                "errors": [],
            }
            workspace = ReconWorkspace()
            workspace.set_model(StructureModel())
            for fn in spec["funcs"]:
                try:
                    cfunc, idx, lv = _prepare_scan(fn)
                    obj = VariableObject(lv, idx)
                    visitor_cls = (
                        NewDeepSearchVisitor
                        if spec.get("visitor") == "deep"
                        else NewShallowSearchVisitor
                    )
                    visitor = visitor_cls(cfunc, 0, obj, workspace, consts=session.consts)
                    visitor.process()
                except Exception:
                    entry["errors"].append({"func": fn, "error": traceback.format_exc()})
            try:
                workspace.model.resolve_types()
            except Exception:
                entry["errors"].append(
                    {"func": "<resolve_types>", "error": traceback.format_exc()}
                )
            for m in workspace.model.items:
                entry["members"].append(
                    {
                        "offset": int(m.offset),
                        "size": int(m.size),
                        "type_name": str(m.type_name),
                        "enabled": bool(m.enabled),
                        "is_array": bool(m.is_array),
                        "score": int(m.score),
                    }
                )
            results.append(entry)

        # Negative-offset (CONTAINING_RECORD) workflow — paper §3.3.4.
        for struct_name, spec in BENCH_NEGATIVE_OFFSETS.items():
            entry: dict[str, Any] = {
                "struct": struct_name,
                "fields": spec["fields"],
                "members": [],
                "errors": [],
            }
            try:
                fn = spec["funcs"][0]
                members, errs = _scan_neg_offset(
                    fn,
                    var_idx=0,
                    magic_comment=spec["magic_comment"],
                )
                entry["errors"] = [{"func": fn, "error": e} for e in errs]
                entry["members"] = members
            except Exception:
                entry["errors"].append(
                    {"func": "<neg_offset>", "error": traceback.format_exc()}
                )
            results.append(entry)
    finally:
        with contextlib.suppress(Exception):
            session.close()
    return results


def main() -> None:
    out_path = os.environ.get("TREX_BENCH_OUT")
    payload: dict[str, Any] = {"results": [], "fatal": None}
    try:
        ida_auto.auto_wait()
        payload["results"] = run()
    except Exception:
        payload["fatal"] = traceback.format_exc()
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps(payload, indent=1), encoding="utf-8")
    idaapi.qexit(0 if payload["fatal"] is None else 1)


if __name__ == "__main__":
    main()
