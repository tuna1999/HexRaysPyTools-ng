"""Test Class."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.browser.registered_class import Class


def test_class_init_default_fields() -> None:
    cls = Class(name="Foo")
    assert cls.name == "Foo"
    assert cls.ordinal == 0
    assert cls.vtables == {}
    assert cls.selected is False


def test_class_has_function_empty() -> None:
    """has_function returns False when vtables is empty."""
    cls = Class(name="Foo")
    assert cls.has_function("anything") is False


def test_class_has_function_matches() -> None:
    """has_function returns True when a vtable function name matches."""
    cls = Class(name="Foo")
    vf = MagicMock()
    vf.name = "doSomething"
    vtable = MagicMock()
    vtable.virtual_functions = [vf]
    cls.vtables[0] = vtable
    assert cls.has_function("doSomething") is True


def test_class_has_function_no_match() -> None:
    """has_function returns False when no vtable function name matches."""
    cls = Class(name="Foo")
    vf = MagicMock()
    vf.name = "doSomething"
    vtable = MagicMock()
    vtable.virtual_functions = [vf]
    cls.vtables[0] = vtable
    assert cls.has_function("doNothing") is False


def test_class_repr_doesnt_crash() -> None:
    """Class() doesn't have a custom __repr__; default is fine (not 'class_name' in output)."""
    cls = Class(name="Foo")
    r = repr(cls)
    assert "Foo" in r
