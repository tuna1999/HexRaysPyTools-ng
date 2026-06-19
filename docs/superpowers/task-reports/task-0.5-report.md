# Task 0.5 Report: pure/name_mangle.py

## Status

**DONE_WITH_CONCERNS** — Two minimal, behavior-preserving deviations from the
brief's verbatim source were required to make the brief's own tests pass. The
brief's regex and implementation, taken verbatim, fail 2 of the 9 documented
tests. Details below.

## Commit

- **SHA:** `6558327559bd513656114edc3117a18a92d249e8`
- **Subject:** `feat(pure): add name_mangle.sanitize_c_name (replaces common.py)`
- **Branch:** `master`
- **Files:**
  - `src/hexrays_pytools/pure/name_mangle.py` (new, 51 lines)
  - `tests/pure/test_name_mangle.py` (new, 56 lines)

## TDD Summary

- **RED:** Brief's verbatim implementation fails 2/9 tests
  (`test_colon_colon_replaced_with_underscore`,
  `test_template_angle_brackets_replaced`) because the regex literal `:::+`
  requires **3+** colons and never matches the `::` namespace separator. With
  the early-return guard from the original `common.py` also removed, `std::vector`
  passes through unchanged as `std::vector` instead of `std_vector`.
- **GREEN:** After the two fixes below, all **9/9 tests pass**.

```
9 passed in 0.02s
```

- **mypy --strict:** `Success: no issues found in 1 source file`
- **ruff check:** `All checks passed!`

## Deviations from Brief (DONE_WITH_CONCERNS)

### Deviation 1 — Regex `:::+` -> `::+` (required by rule #2 + tests)

The brief's regex used `:::+`, which matches only 3-or-more consecutive colons.
The `::` namespace separator (exactly 2 colons) was never matched, so:

- `std::vector` stayed `std::vector` (expected `std_vector`)
- `a::b::c` stayed `a::b::c` (expected `a_b_c`)
- `std::vector<int>` stayed `std::vector_t_int_t_` (expected
  `std_vector_t_int_t_`)

The original `refs/.../core/common.py` papered over this with an early-return
guard (`if not BAD_C_NAME_PATTERN.findall(name): return name`) combined with a
long operator-replacement block. The rewrite dropped both, exposing the bug.

**Fix:** `r":::+|..."` -> `r"::+|..."` (one character change). This makes rule #2
(`::` -> `_`) hold, which is the stated purpose of the rewrite.

### Deviation 2 — Added `name = name.replace(",", "_t_")` (required by brief test)

The brief's test `test_template_angle_brackets_replaced` asserts:

```python
assert sanitize_c_name("map<string,int>") == "map_t_string_t_int_t_"
```

The brief's algorithm turns `map<string,int>` into `map_t_string,int_t_` after
the `<`/`>` replacement. The comma is then an "illegal character" stripped by
the regex split/join, producing `map_t_stringint_t_` (no separator between
`string` and `int`) — **not** the expected `map_t_string_t_int_t_`.

**Fix:** add `name = name.replace(",", "_t_")` so each template argument stays
delimited. This is consistent with how `<` and `>` are treated and matches the
documented test expectation.

### Deviation 3 (cosmetic) — ruff compliance

The brief explicitly permits minimal behavior-preserving fixes for ruff. Two
ruff rules fired on the verbatim source:

- **I001** (import sorting): added a blank line between
  `from __future__ import annotations` and `import re`.
- **RET504** (unnecessary assign before return): inlined the final
  `return "_".join(filter(len, _ILLEGAL_CHARS.split(name)))`.

These are purely stylistic; behavior is identical.

## Self-Review

- [x] 9/9 documented tests pass
- [x] mypy --strict clean
- [x] ruff clean
- [x] Commit uses the brief's exact message
- [x] Only the two required files were staged/committed (no `refs/` or
      unrelated docs swept in)
- [x] Deviations are documented inline in the source with `NOTE:` comments
- [x] Test file matches the brief verbatim
- [!] The brief is internally inconsistent: its documented rules (#2, #7) and
      test expectations cannot be satisfied by its verbatim implementation.
      A future brief revision should either (a) restore the early-return guard
      and accept `std::vector` as output, or (b) ship the `::+` + comma fixes
      so the documented behavior holds.
