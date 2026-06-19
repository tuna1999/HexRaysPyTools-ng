# Task 0.7 Report: pure/toml_template.py

## Status: DONE_WITH_CONCERNS

All 6 tests pass green, mypy --strict is clean, ruff is clean, and the commit
lands with the exact message specified in the brief. The concerns are
deviations from the brief's verbatim content, required to make the brief's
own tests pass. Every deviation is documented below.

## Commit

- SHA: `736505cb78505c24539c892cb66c95666fbc0f5f`
- Subject: `feat(pure): add toml_template parser/renderer (stdlib tomllib)`
- Files (4):
  - `src/hexrays_pytools/pure/toml_template.py` (new)
  - `tests/pure/test_toml_template.py` (new)
  - `tests/fixtures/__init__.py` (new, empty)
  - `tests/fixtures/sample_templated_types.toml` (new)

## TDD Summary

1. **Created 4 files** exactly as specified in the brief.
2. **RED (empirical, not aspirational):** Ran `pytest tests/pure/test_toml_template.py`
   against the verbatim implementation. Result: **4 passed, 2 failed** — not the
   6/6 the brief's note promised.
   - `test_render_single_param_template` failed with
     `ValueError: unexpected '{' in field name` from `str.format`.
   - `test_render_two_param_template` failed with the same `ValueError`.
3. **Root-caused 3 independent defects** in the brief content (see below).
4. **Applied minimal fixes** to reach GREEN (6/6 pass).
5. **Re-ran:** `pytest` 6/6 green, `mypy --strict` clean, `ruff check` clean.
6. **Committed** with the exact brief message.

## Final Verification

```
$ python -m pytest tests/pure/test_toml_template.py -v
test_parse_valid_toml                     PASSED
test_parse_invalid_toml_returns_err       PASSED
test_render_single_param_template         PASSED
test_render_two_param_template            PASSED
test_render_wrong_arg_count_returns_err   PASSED
test_render_unknown_template_returns_err  PASSED
6 passed

Full suite: 31 passed, 94.68% aggregate coverage (toml_template.py at 93%).

$ python -m mypy --strict src/hexrays_pytools/pure/toml_template.py
Success: no issues found in 1 source file

$ python -m ruff check src/hexrays_pytools/pure/toml_template.py tests/pure/test_toml_template.py tests/fixtures/
All checks passed!
```

## Defects in the Brief Content (and the minimal fixes applied)

The brief's note asserts "the current brief has the FIXED test cases... Verify
tests pass as-is." Empirically they do **not** pass as-is. Three mutually
independent inconsistencies between the brief's `toml_template.py`, the TOML
fixture, and the test assertions make 2 of the 6 tests fail. Each is documented
so the brief can be corrected upstream.

### Defect 1 — TOML fixture has unescaped literal braces (CRITICAL, BLOCKER)

**Location:** `tests/fixtures/sample_templated_types.toml`, `struct` fields.

The brief's `render_template` calls `template["struct"].format(*args)`. Python's
`str.format` treats every `{` and `}` as a field marker. The fixture's `struct`
strings contain raw C braces:

```toml
struct = """
struct std_vector_{1} {
    {0} *_Myfirst;
    ...
};
"""
```

`"..._{1} {\n ...".format(...)` raises `ValueError: unexpected '{' in field name`
because the lone `{` after `_{1}` is not a valid field name and is not escaped.

The brief's own module docstring documents the correct convention:
`struct = "struct ida_type_{1} {{ {0} field; }};"` (literal braces doubled to
`{{`/`}}`). The fixture does not follow that convention.

**Fix applied:** Escape all literal C braces in both fixture `struct` values
(`{` → `{{`, `}` → `}}`), leaving the real tokens `{0}`, `{1}`, `{2}`, `{3}`
as single braces. This aligns the fixture with the module's documented format.

### Defect 2 — Tests assert `_PTR`-mangled names that the brief's code never produces (CRITICAL)

**Location:** `tests/pure/test_toml_template.py`, lines asserting on rendered output.

The brief's verbatim `render_template` does a plain `template["struct"].format(*args)`
with no name mangling. With `args = ["int *", "pInt"]` and token `{0}` substituted
literally, the rendered decl contains `int * *_Myfirst`, **not** `int_PTR *_Myfirst`.

Yet the tests assert:
```python
assert "int_PTR *_Myfirst" in decl          # test_render_single_param_template
assert "char_PTR second" in decl            # test_render_two_param_template
```

Plain `.format` cannot yield `_PTR`. Some `*` → `_PTR` mangling is required.

**Investigated option (rejected):** Using the existing
`pure.name_mangle.sanitize_c_name` (Task 0.5). It produces `"int__PTR"` and
`"char__PTR"` (double underscore — space is a split boundary and gets rejoined
with `_`), which does **not** match the test's expected `int_PTR` / `char_PTR`
(single underscore). So the full demangled-name mangler is the wrong transform
here.

**Fix applied:** Added a small private helper `_to_field_type(actual)` that
performs exactly the mangling the tests' hardcoded strings mandate:
`actual.replace("*", "_PTR").replace(" ", "")`. This yields `int *` → `int_PTR`
and `char *` → `char_PTR`, matching the assertions exactly. The helper is
documented with its rules and examples.

### Defect 3 — Module docstring's token-layout claim contradicts the test args (MINOR)

**Location:** Module docstring (and inline comment) describing token layout.

The brief's docstring states: *"for N type params, tokens 0..N-1 are actual
types and tokens N..2N-1 are pretty print tokens"* — i.e. a contiguous
[actuals...][pretties...] layout.

The test args contradict this. For the 2-param `std::map<K,V>` case the args
are `["int", "pInt", "char *", "pChar"]` — interleaved
`[actual_K, pretty_K, actual_V, pretty_V]`. The `base_name = "std_map_{1}_{3}"`
uses the odd-indexed pretty tokens, and `struct` uses `{0}` (actual) and `{2}`
(actual). The actual/pretty semantics are even-index/odd-index, not first-half/
second-half.

**Fix applied:** Corrected the module docstring and the inline comment to
describe the actual interleaved layout
(`[actual_0, pretty_0, actual_1, pretty_1, ...]`), and updated the render logic
to mangle even indices and pass odd indices through. This is consistent with
both the test args and the format strings in the fixture.

## Self-Review

- **Verbatim vs. fix tension:** I prioritized a working, internally consistent
  implementation over mechanical fidelity to a brief that was provably
  self-inconsistent. Each fix is the smallest change that resolves the
  inconsistency without altering the brief's stated design (TOML parsing via
  stdlib `tomllib`, `Result`-based error handling, 2*N arg contract).
- **No scope creep:** I did not add features beyond what the tests require.
  `_to_field_type` handles exactly the two cases the tests exercise (`int` and
  `pointer-type-with-space`). It is not a general C++ demangler; that role
  belongs to `sanitize_c_name` in `name_mangle.py`.
- **No behavioral surprise for callers:** `parse_toml_template` is byte-for-byte
  the brief's version. `render_template` adds mangling on actual-type tokens
  only; the arg-count and format-error paths are unchanged.
- **Import-ordering lint:** Ruff flagged the brief's unsorted imports
  (`from __future__` immediately followed by `import tomllib` with no blank
  line, and a missing blank line between stdlib and local imports in the test
  file). I applied the trivial `isort`-style fixes (blank lines only) so `ruff
  check` passes; no reordering of symbols.
- **Coverage gate:** Running the single test file fails the project's
  `--cov-fail-under=80` aggregate (53%) only because other modules' own tests
  are not executed. The full `pytest` run (all test files) is at 94.68%, and
  `toml_template.py` alone is at 93%. This is a known artifact of file-scoped
  invocation, not a coverage defect in this task.
- **`tests/fixtures/__init__.py`:** Created empty, as specified. Ruff accepts
  empty files.

## Recommendation for Upstream

Update the brief to:
1. Escape literal braces in the fixture's `struct` values (`{{`/`}}`).
2. Add the `_to_field_type` helper (or document that `*` → `_PTR` mangling is
   the render contract) and call it on actual-type tokens.
3. Correct the token-layout sentence to the interleaved form.
4. Drop the "tests pass as-is" claim, or re-verify after the above.

Once the brief is corrected, the verbatim files will pass without the fixes
described here.
