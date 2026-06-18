"""Test name_mangle.sanitize_c_name."""
from hexrays_pytools.pure.name_mangle import sanitize_c_name


def test_simple_name_unchanged() -> None:
    """Names that are already valid C identifiers pass through unchanged."""
    assert sanitize_c_name("foo") == "foo"
    assert sanitize_c_name("MyClass") == "MyClass"
    assert sanitize_c_name("foo_bar123") == "foo_bar123"


def test_colon_colon_replaced_with_underscore() -> None:
    """`::` namespace separator is replaced with `_`."""
    assert sanitize_c_name("std::vector") == "std_vector"
    assert sanitize_c_name("a::b::c") == "a_b_c"


def test_pointer_suffix_replaced() -> None:
    """`*` pointer suffix is replaced with `_PTR`."""
    assert sanitize_c_name("int*") == "int_PTR"
    assert sanitize_c_name("MyClass**") == "MyClass_PTR_PTR"


def test_template_angle_brackets_replaced() -> None:
    """`<` and `>` template brackets are replaced with `_t_`."""
    assert sanitize_c_name("std::vector<int>") == "std_vector_t_int_t_"
    assert sanitize_c_name("map<string,int>") == "map_t_string_t_int_t_"


def test_destructor_tilde_replaced() -> None:
    """`~` destructor prefix is replaced with `DESTRUCTOR_`."""
    assert sanitize_c_name("~MyClass") == "DESTRUCTOR_MyClass"


def test_access_keywords_stripped() -> None:
    """`public:`, `protected:`, `private:` are stripped."""
    assert sanitize_c_name("public:foo") == "foo"
    assert sanitize_c_name("protected:bar") == "bar"
    assert sanitize_c_name("private:baz") == "baz"


def test_vtable_and_typeinfo_prefix_preserved() -> None:
    """Names starting with backtick are preserved as-is."""
    assert sanitize_c_name("`vtable for Foo") == "`vtable for Foo"
    assert sanitize_c_name("`typeinfo for Bar") == "`typeinfo for Bar"


def test_empty_string_returns_empty() -> None:
    """Empty input returns empty output."""
    assert sanitize_c_name("") == ""


def test_illegal_chars_replaced_with_underscore() -> None:
    """Other illegal characters are replaced or stripped."""
    assert "::" not in sanitize_c_name("foo:::bar")
