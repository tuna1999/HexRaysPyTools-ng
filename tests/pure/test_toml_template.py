"""Test toml_template.parse_toml_template and render_template."""
from pathlib import Path

from hexrays_pytools.pure.toml_template import parse_toml_template, render_template

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_templated_types.toml"


def test_parse_valid_toml() -> None:
    """Valid TOML is parsed into a dict of templates."""
    result = parse_toml_template(FIXTURE.read_text())
    assert result.is_ok
    templates = result.unwrap()
    assert "std::vector<T>" in templates
    assert "std::map<K,V>" in templates


def test_parse_invalid_toml_returns_err() -> None:
    """Malformed TOML returns an error result."""
    result = parse_toml_template("not valid toml [[[")
    assert not result.is_ok
    assert result.error is not None


def test_render_single_param_template() -> None:
    """A template with 1 type param renders correctly with 2 args (actual, pretty)."""
    result = parse_toml_template(FIXTURE.read_text())
    templates = result.unwrap()
    rendered = render_template(templates["std::vector<T>"], ["int *", "pInt"])
    assert rendered.is_ok
    type_name, decl = rendered.unwrap()
    assert type_name == "std_vector_pInt"
    assert "int_PTR *_Myfirst" in decl


def test_render_two_param_template() -> None:
    """A template with 2 type params renders correctly with 4 args (actual, pretty, actual, pretty)."""
    result = parse_toml_template(FIXTURE.read_text())
    templates = result.unwrap()
    rendered = render_template(templates["std::map<K,V>"], ["int", "pInt", "char *", "pChar"])
    assert rendered.is_ok
    type_name, decl = rendered.unwrap()
    assert type_name == "std_map_pInt_pChar"
    assert "int first" in decl
    assert "char_PTR second" in decl


def test_render_wrong_arg_count_returns_err() -> None:
    """Wrong number of args returns an error."""
    result = parse_toml_template(FIXTURE.read_text())
    templates = result.unwrap()
    rendered = render_template(templates["std::vector<T>"], ["int *", "pInt", "extra"])
    assert not rendered.is_ok


def test_render_unknown_template_returns_err() -> None:
    """Render with 0 args (need 2) returns an error."""
    result = parse_toml_template(FIXTURE.read_text())
    templates = result.unwrap()
    rendered = render_template(templates["std::vector<T>"], [])
    assert not rendered.is_ok
