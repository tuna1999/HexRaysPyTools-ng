"""Score trex_bench raw evidence against ground truth (TRex-style).

Usage: python score_trex_bench.py RAW_O0.json RAW_O2.json

Per ground-truth field (offset, size), the best matching *enabled* member
(after resolve_types) scores:
    1.0  offset AND size exact
    0.5  offset exact, size differs (right location, wrong behavior capture)
    0.0  no member at that offset
member_precision = enabled members landing on a ground-truth offset / enabled
members (hallucinated offsets penalized). structs_full = structs where every
field scored 1.0.

Prints `METRIC name=value` lines. Primary: recon_score (-O0). Deterministic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

EXACT = 1.0
OFFSET_ONLY = 0.5


def _score_level(raw: dict[str, Any]) -> dict[str, float]:
    if raw.get("fatal"):
        raise SystemExit(f"harness fatal error:\n{raw['fatal']}")
    total_fields = 0
    field_score = 0.0
    exact_fields = 0
    members_total = 0
    members_on_gt = 0
    structs_full = 0
    structs = 0

    for entry in raw["results"]:
        structs += 1
        fields = [(int(o), int(s)) for o, s in entry["fields"]]
        offsets_gt = {o for o, _ in fields}
        members = [m for m in entry["members"] if m["enabled"]]
        all_exact = True
        for off, size in fields:
            total_fields += 1
            best = 0.0
            for m in members:
                if m["offset"] != off:
                    continue
                best = EXACT if m["size"] == size else max(best, OFFSET_ONLY)
            field_score += best
            if best >= EXACT:
                exact_fields += 1
            else:
                all_exact = False
        members_total += len(members)
        members_on_gt += sum(1 for m in members if m["offset"] in offsets_gt)
        if all_exact:
            structs_full += 1

    n = max(total_fields, 1)
    return {
        "recon_score": field_score / n,
        "field_recall_exact": exact_fields / n,
        "member_precision": (members_on_gt / members_total) if members_total else 0.0,
        "structs_full": float(structs_full),
        "structs_total": float(structs),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"usage: {argv[0]} RAW_O0.json RAW_O2.json", file=sys.stderr)
        return 2
    levels: dict[str, dict[str, float]] = {}
    for tag, path in (("o0", argv[1]), ("o2", argv[2])):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        levels[tag] = _score_level(raw)

    o0, o2 = levels["o0"], levels["o2"]
    print(f"METRIC recon_score={o0['recon_score']:.4f}")
    print(f"METRIC recon_score_o2={o2['recon_score']:.4f}")
    print(f"METRIC field_recall_exact={o0['field_recall_exact']:.4f}")
    print(f"METRIC field_recall_exact_o2={o2['field_recall_exact']:.4f}")
    print(f"METRIC member_precision={o0['member_precision']:.4f}")
    print(f"METRIC member_precision_o2={o2['member_precision']:.4f}")
    print(f"METRIC structs_full={o0['structs_full']:.0f}")
    print(f"METRIC structs_full_o2={o2['structs_full']:.0f}")

    # Per-struct breakdown to stderr for the research loop.
    for tag in ("o0", "o2"):
        print(f"--- {tag} summary ---", file=sys.stderr)
        for k, v in levels[tag].items():
            print(f"  {k}={v}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
