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
