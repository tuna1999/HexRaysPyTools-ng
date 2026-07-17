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
