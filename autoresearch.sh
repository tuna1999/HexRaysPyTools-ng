#!/usr/bin/env bash
# Autoresearch benchmark: scanner type-reconstruction quality (TRex-style).
#
# Workload (deterministic, offline):
#   1. Build verification/trex_bench.c at -O0 and -O2 with a fixed local GCC
#      (cached — rebuilt only when missing).
#   2. For each binary: fresh temp database, run the HexRaysPyTools-ng scanner
#      headless via ida batch -S (verification/trex_bench_ida.py), dump raw member
#      evidence JSON.
#   3. Score evidence against ground truth (verification/score_trex_bench.py)
#      and print METRIC lines.
#
# Primary metric: recon_score (-O0, higher = better).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
if WIN_ROOT="$(cd "$ROOT" && pwd -W 2>/dev/null)"; then :; else WIN_ROOT="$ROOT"; fi

IDA_GUI="${IDA_GUI:-C:/Program Files/IDA Professional 9.4/ida.exe}"
GCC_CANDIDATES=("${GCC:-}" /d/ProgramFiles/MingW64/bin/gcc.exe gcc)
GCC=""
for c in "${GCC_CANDIDATES[@]}"; do
    if [ -n "$c" ] && command -v "$c" >/dev/null 2>&1; then GCC="$c"; break; fi
done
[ -n "$GCC" ] || { echo "ERROR: no C compiler found (set GCC=...)" >&2; exit 1; }
[ -f "$IDA_GUI" ] || { echo "ERROR: ida not found at: $IDA_GUI (set IDA_GUI=...)" >&2; exit 1; }

SRCS="$ROOT/verification/trex_bench.c"
IDA_SCRIPT="$WIN_ROOT/verification/trex_bench_ida.py"
LOGDIR="$ROOT/verification/logs"
mkdir -p "$LOGDIR"

build() { # build <opt-flag> <exe-name>
    local opt="$1" exe="$ROOT/verification/$2"
    [ -f "$exe" ] && return 0
    echo "building $2 with $GCC $opt ..." >&2
    "$GCC" $opt -g0 -fno-inline -o "$exe" "$SRCS" >&2
}

run_ida() { # run_ida <exe-path> <out-json-path> <tag>
    local exe="$1" out="$2" tag="$3"
    local work
    work="$(mktemp -d)"
    trap 'rm -rf "$work"' RETURN
    cp "$exe" "$work/bench.exe"
    rm -f "$out"
    TREX_BENCH_OUT="$out" timeout 600 "$IDA_GUI" -A -c \
        -S"$IDA_SCRIPT" -L"$work/ida_$tag.log" "$work/bench.exe" \
        < /dev/null > /dev/null 2>&1 || echo "ida ($tag) rc=$? (continuing; JSON is the contract)" >&2
    if [ ! -f "$out" ]; then
        echo "ERROR: no results JSON for $tag (see $work/ida_$tag.log)" >&2
        tail -40 "$work/ida_$tag.log" >&2 || true
        return 1
    fi
    cp "$work/ida_$tag.log" "$LOGDIR/ida_$tag.log" 2>/dev/null || true
}

build -O0 trex_bench_o0.exe
build -O2 trex_bench_o2.exe

run_ida "$ROOT/verification/trex_bench_o0.exe" "$LOGDIR/trex_bench_raw_o0.json" o0
run_ida "$ROOT/verification/trex_bench_o2.exe" "$LOGDIR/trex_bench_raw_o2.json" o2

uv run --project "$ROOT" python "$ROOT/verification/score_trex_bench.py" \
    "$LOGDIR/trex_bench_raw_o0.json" "$LOGDIR/trex_bench_raw_o2.json"
