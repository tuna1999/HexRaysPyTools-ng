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
