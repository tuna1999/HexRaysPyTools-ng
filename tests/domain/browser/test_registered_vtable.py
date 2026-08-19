"""Test RegisteredVTable."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.browser.registered_vtable import (
    RegisteredVTable,
    VirtualMethod,
)


def test_registered_vtable_defaults() -> None:
    v = RegisteredVTable(name="vtable", ordinal=42)
    assert v.name == "vtable"
    assert v.ordinal == 42
    assert v.virtual_functions == []


def test_virtual_method_defaults() -> None:
    m = VirtualMethod(name="foo")
    assert m.name == "foo"
    assert m.address == 0
    assert m.parents == []


def test_tooltip_with_tinfo() -> None:
    v = RegisteredVTable(name="vtable", class_name="Foo")
    v.tinfo = MagicMock()
    v.tinfo.dstr.return_value = "struct Foo_vtable { void(*bar)(); }"
    assert "Foo_vtable" in v.tooltip()


def test_tooltip_without_tinfo() -> None:
    v = RegisteredVTable(name="vtable", class_name="Foo", offset=0x10)
    hint = v.tooltip()
    assert "Foo" in hint
    assert "vtable" in hint
    assert "0x10" in hint


def test_populate_virtual_functions_uses_session_demangled_cache(monkeypatch) -> None:
    idaapi = __import__("idaapi")
    idaapi.get_imagebase.return_value = 0x1000
    member = MagicMock()
    member.name = "bar"
    member.offset = 0
    member.type = MagicMock()

    class _Udt(list):
        pass

    udt = _Udt([member])
    monkeypatch.setattr(idaapi, "udt_type_data_t", lambda: udt)
    tinfo = MagicMock()
    tinfo.get_udt_details.return_value = True
    vtable = RegisteredVTable(name="Foo_vtbl", tinfo=tinfo, class_name="Foo")

    vtable.populate_virtual_functions({"Foo_bar": {0x1234}})

    assert len(vtable.virtual_functions) == 1
    assert vtable.virtual_functions[0].addresses == [0x1234]
