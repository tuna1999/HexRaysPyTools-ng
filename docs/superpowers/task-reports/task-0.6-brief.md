# Task 0.6 Brief: pure/scoring.py

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\pure\scoring.py`
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\pure\test_scoring.py`

## Required Content (verbatim)

### `src/hexrays_pytools/pure/scoring.py`

```python
"""Heuristic scoring for struct member candidates.

Pure function — no IDA dependency. Used to rank competing candidates for the
same offset during `Resolve Conflicts` in the Structure Builder.

Scoring factors (higher = better):
    + log2(size) for size 1, 2, 4, 8
    + 0x2000 if name contains 'vtable'
    - 0x1000 if name starts with '_' (likely auto-generated)
    - 0xFFFF if size is 0 (invalid member)
"""
from __future__ import annotations

_VTABLE_BONUS = 0x2000
_UNDERSCORE_PENALTY = 0x1000
_ZERO_SIZE_PENALTY = 0xFFFF

_SIZE_SCORE: dict[int, int] = {1: 0, 2: 1, 4: 2, 8: 3}


def score_member(name: str, type_size: int) -> int:
    """Return a numeric score for a struct member candidate.

    Higher score = better candidate when resolving collisions.
    Negative scores indicate invalid members.
    """
    if type_size <= 0:
        return -_ZERO_SIZE_PENALTY

    score = _SIZE_SCORE.get(type_size, type_size.bit_length() - 1)

    if name.startswith("_"):
        score -= _UNDERSCORE_PENALTY
    if "vtable" in name.lower():
        score += _VTABLE_BONUS

    return score
```

### `tests/pure/test_scoring.py`

```python
"""Test scoring.score_member."""
from hexrays_pytools.pure.scoring import score_member


def test_simple_int_field_score() -> None:
    """A 4-byte int field with a good name scores high."""
    score = score_member("size", 4)
    assert score > 0


def test_larger_alignment_scores_higher() -> None:
    """Bigger primitive types score higher (better alignment)."""
    assert score_member("foo", 8) > score_member("foo", 4)
    assert score_member("foo", 4) > score_member("foo", 2)
    assert score_member("foo", 2) > score_member("foo", 1)


def test_underscore_prefix_name_penalized() -> None:
    """Names starting with `_` (likely auto-generated) score lower."""
    assert score_member("_size", 4) < score_member("size", 4)


def test_vtable_marker_name_bonus() -> None:
    """Names containing `vtable` get a bonus."""
    assert score_member("vtable_ptr", 8) > score_member("data", 8)


def test_zero_size_returns_negative() -> None:
    """Zero-size members get a low (or negative) score."""
    assert score_member("foo", 0) < 0


def test_scoring_is_pure() -> None:
    """score_member is a pure function — same inputs always give same output."""
    assert score_member("foo", 4) == score_member("foo", 4)
```

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/pure/test_scoring.py -v
python -m mypy --strict src/hexrays_pytools/pure/scoring.py
python -m ruff check src/hexrays_pytools/pure/scoring.py tests/pure/test_scoring.py
```

## Commit

```bash
git add src/hexrays_pytools/pure/scoring.py tests/pure/test_scoring.py
git commit -m "feat(pure): add scoring.score_member for collision resolution"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-0.6-report.md`
