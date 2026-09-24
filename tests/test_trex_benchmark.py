"""Benchmark scores use fixture ground truth, not stale raw metadata."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "verification"))

from score_trex_bench import _score_level  # noqa: E402


def test_missing_negative_offset_inner_field_reduces_reconstruction_score() -> None:
    raw = {
        "results": [
            {
                "struct": "NegOuter",
                "fields": [[0, 4]],  # older saved runs omitted the actual inner field
                "members": [{"offset": 0, "size": 4, "enabled": True}],
                "errors": [],
            }
        ]
    }

    assert _score_level(raw)["recon_score"] == 0.5
