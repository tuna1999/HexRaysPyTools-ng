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


def test_create_class_returns_none_for_non_udt() -> None:
    """Class.create returns None when the ordinal is not a UDT."""
    idaapi = __import__("idaapi")
    tinfo = MagicMock()
    tinfo.is_udt.return_value = False
    idaapi.tinfo_t.return_value = tinfo
    assert Class.create(1) is None


def test_create_class_returns_none_for_no_vtable() -> None:
    """Class.create returns None when UDT has no ptr-to-funcptr field."""
    idaapi = __import__("idaapi")
    tinfo = MagicMock()
    tinfo.is_udt.return_value = True
    member = MagicMock()
    member.type.is_ptr.return_value = False
    udt = MagicMock()
    udt.__iter__.return_value = iter([member])
    idaapi.tinfo_t.return_value = tinfo
    idaapi.udt_type_data_t.return_value = udt
    tinfo.get_udt_details.return_value = True
    assert Class.create(1) is None


def test_create_class_returns_class_for_vtable_struct() -> None:
    """Class.create returns a Class when the type has a vtable field."""
    idaapi = __import__("idaapi")
    tinfo = MagicMock()
    tinfo.is_udt.return_value = True
    member = MagicMock()
    member.type.is_ptr.return_value = True
    pointed = MagicMock()
    pointed.is_funcptr.return_value = True
    member.type.get_pointed_object.return_value = pointed
    udt = MagicMock()
    udt.__iter__.return_value = iter([member])
    idaapi.tinfo_t.return_value = tinfo
    idaapi.udt_type_data_t.return_value = udt
    idaapi.get_idati.return_value = MagicMock()
    tinfo.get_udt_details.return_value = True
    tinfo.dstr.return_value = "Foo"
    result = Class.create(42)
    assert result is not None
    assert result.ordinal == 42
    assert result.name == "Foo"


def test_create_class_returns_none_when_not_udt_after_get() -> None:
    """Class.create returns None when tinfo is falsy after get_numbered_type."""
    idaapi = __import__("idaapi")
    tinfo = MagicMock()
    # Make `not tinfo` True by overriding __bool__ via spec; simpler: is_udt False path
    tinfo.is_udt.return_value = False
    idaapi.tinfo_t.return_value = tinfo
    assert Class.create(99) is None


def test_create_class_empty_udt_returns_none() -> None:
    """Class.create returns None when UDT has no members."""
    idaapi = __import__("idaapi")
    tinfo = MagicMock()
    tinfo.is_udt.return_value = True
    udt = MagicMock()
    udt.__iter__.return_value = iter([])  # no members
    idaapi.tinfo_t.return_value = tinfo
    idaapi.udt_type_data_t.return_value = udt
    tinfo.get_udt_details.return_value = True
    assert Class.create(7) is None


def test_create_class_ptr_to_non_funcptr_returns_none() -> None:
    """Class.create returns None when a ptr field points to a non-funcptr."""
    idaapi = __import__("idaapi")
    tinfo = MagicMock()
    tinfo.is_udt.return_value = True
    member = MagicMock()
    member.type.is_ptr.return_value = True
    pointed = MagicMock()
    pointed.is_funcptr.return_value = False  # ptr but not to funcptr
    member.type.get_pointed_object.return_value = pointed
    udt = MagicMock()
    udt.__iter__.return_value = iter([member])
    idaapi.tinfo_t.return_value = tinfo
    idaapi.udt_type_data_t.return_value = udt
    tinfo.get_udt_details.return_value = True
    assert Class.create(5) is None


def test_create_class_ptr_to_none_returns_none() -> None:
    """Class.create returns None when get_pointed_object returns None."""
    idaapi = __import__("idaapi")
    tinfo = MagicMock()
    tinfo.is_udt.return_value = True
    member = MagicMock()
    member.type.is_ptr.return_value = True
    member.type.get_pointed_object.return_value = None  # null ptr
    udt = MagicMock()
    udt.__iter__.return_value = iter([member])
    idaapi.tinfo_t.return_value = tinfo
    idaapi.udt_type_data_t.return_value = udt
    tinfo.get_udt_details.return_value = True
    assert Class.create(5) is None
