"""Test TemplatedTypes."""
from hexrays_pytools.domain.templated.templated_types import TemplatedTypes


def test_load_bundled_types() -> None:
    """Default construction loads bundled templated types."""
    t = TemplatedTypes()
    assert "std::vector<T>" in t.keys


def test_custom_path_missing_file() -> None:
    """Custom path that doesn't exist results in empty keys."""
    t = TemplatedTypes(custom_path="/nonexistent/path.toml")
    assert t.keys == []


def test_get_types_for_known_key() -> None:
    """get_types returns the type-param list for a known key."""
    t = TemplatedTypes()
    types = t.get_types("std::vector<T>")
    assert types == ["T"]


def test_get_types_for_unknown_key() -> None:
    """get_types returns None for an unknown key."""
    t = TemplatedTypes()
    assert t.get_types("std::unknown<X>") is None


def test_get_decl_str_renders_template() -> None:
    """get_decl_str returns (name, decl) for valid args."""
    t = TemplatedTypes()
    result = t.get_decl_str("std::vector<T>", ["int *", "pInt"])
    assert result.is_ok
    name, decl = result.unwrap()
    assert name == "std_vector_pInt"
    assert "int_PTR *_Myfirst" in decl


def test_get_decl_str_unknown_key() -> None:
    """get_decl_str returns err for unknown key."""
    t = TemplatedTypes()
    result = t.get_decl_str("std::unknown<X>", ["T", "pT"])
    assert not result.is_ok
