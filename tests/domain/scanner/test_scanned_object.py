"""Test the ScanObject factory hierarchy (domain/scanner/scanned_object.py)."""
from __future__ import annotations

from unittest.mock import MagicMock

import idaapi  # type: ignore[import-not-found]  # via mock_ida

from hexrays_pytools.domain.scanner.scanned_object import (
    SO_CALL_ARGUMENT,
    SO_GLOBAL_OBJECT,
    SO_LOCAL_VARIABLE,
    SO_MEMORY_ALLOCATOR,
    SO_RETURNED_OBJECT,
    SO_STRUCT_POINTER,
    SO_STRUCT_REFERENCE,
    CallArgObject,
    GlobalVariableObject,
    MemoryAllocationObject,
    ReturnedObject,
    ScanObject,
    StructPtrObject,
    StructRefObject,
    VariableObject,
)

# --- SO_* constants -----------------------------------------------------------


def test_so_constants_match_original_values() -> None:
    """SO_* numeric values are part of the on-disk contract — must not drift."""
    # Values copied verbatim from the original ``api.py:80-86``. Any netnode
    # state from prior versions of the plugin depends on these numbers.
    assert SO_LOCAL_VARIABLE == 1
    assert SO_STRUCT_POINTER == 2
    assert SO_STRUCT_REFERENCE == 3
    assert SO_GLOBAL_OBJECT == 4
    assert SO_CALL_ARGUMENT == 5
    assert SO_MEMORY_ALLOCATOR == 6
    assert SO_RETURNED_OBJECT == 7


# --- ScanObject base ----------------------------------------------------------


def test_scan_object_default_constructor() -> None:
    """``ScanObject()`` leaves all fields empty/default."""
    obj = ScanObject()
    assert obj.ea == idaapi.BADADDR
    assert obj.name is None
    assert obj.tinfo is None
    assert obj.id == 0


def test_scan_object_repr_uses_name_when_present() -> None:
    """``__repr__`` shows the name when set, otherwise the id."""
    obj = ScanObject()
    obj.name = "v1"
    assert "v1" in repr(obj)
    obj2 = ScanObject()
    obj2.id = 99
    assert "99" in repr(obj2)


def test_scan_object_equality_and_hash() -> None:
    """Two ScanObjects with same (id, name) are equal + hashable."""
    a = ScanObject()
    a.id = 1
    a.name = "x"
    b = ScanObject()
    b.id = 1
    b.name = "x"
    assert a == b
    assert hash(a) == hash(b)
    # Different name → not equal
    c = ScanObject()
    c.id = 1
    c.name = "y"
    assert a != c


# --- VariableObject -----------------------------------------------------------


def test_variable_object_init() -> None:
    """VariableObject captures the lvar + index + tinfo."""
    lvar = MagicMock()
    lvar.name = "v3"
    lvar.type.return_value = "v3_t"
    obj = VariableObject(lvar, 3)
    assert obj.id == SO_LOCAL_VARIABLE
    assert obj.index == 3
    assert obj.name == "v3"
    assert obj.tinfo == "v3_t"


def test_variable_object_is_target_matches_same_index() -> None:
    """is_target matches cot_var with the same v.idx."""
    obj = VariableObject(MagicMock(name="lvar", type=MagicMock(return_value="t")), 5)
    cexpr = MagicMock()
    cexpr.op = idaapi.cot_var
    cexpr.v.idx = 5
    assert obj.is_target(cexpr) is True

    cexpr.v.idx = 6  # different index
    assert obj.is_target(cexpr) is False

    cexpr.op = idaapi.cot_num  # different op
    cexpr.v.idx = 5
    assert obj.is_target(cexpr) is False


# --- StructPtrObject ----------------------------------------------------------


def test_struct_ptr_object_init() -> None:
    """StructPtrObject captures struct_name + offset."""
    obj = StructPtrObject("MyStruct", 0x10)
    assert obj.id == SO_STRUCT_POINTER
    assert obj.struct_name == "MyStruct"
    assert obj.offset == 0x10


def test_struct_ptr_object_is_target_matches_same_field() -> None:
    """is_target matches cot_memptr with same offset + pointed type."""
    obj = StructPtrObject("MyStruct", 0x10)

    cexpr = MagicMock()
    cexpr.op = idaapi.cot_memptr
    cexpr.m = 0x10
    cexpr.x.type.get_pointed_object.return_value.dstr.return_value = "MyStruct"
    assert obj.is_target(cexpr) is True

    cexpr.m = 0x11  # different offset
    assert obj.is_target(cexpr) is False

    cexpr.m = 0x10
    cexpr.x.type.get_pointed_object.return_value.dstr.return_value = "Other"
    assert obj.is_target(cexpr) is False


# --- StructRefObject ----------------------------------------------------------


def test_struct_ref_object_init() -> None:
    """StructRefObject captures struct_name + offset."""
    obj = StructRefObject("MyStruct", 0x8)
    assert obj.id == SO_STRUCT_REFERENCE
    assert obj.struct_name == "MyStruct"
    assert obj.offset == 0x8


def test_struct_ref_object_is_target_matches_same_field() -> None:
    """is_target matches cot_memref with same offset + type."""
    obj = StructRefObject("MyStruct", 0x8)

    cexpr = MagicMock()
    cexpr.op = idaapi.cot_memref
    cexpr.m = 0x8
    cexpr.x.type.dstr.return_value = "MyStruct"
    assert obj.is_target(cexpr) is True

    cexpr.x.type.dstr.return_value = "Other"
    assert obj.is_target(cexpr) is False


# --- GlobalVariableObject -----------------------------------------------------


def test_global_variable_object_init() -> None:
    """GlobalVariableObject captures obj_ea."""
    obj = GlobalVariableObject(0x401000)
    assert obj.id == SO_GLOBAL_OBJECT
    assert obj.obj_ea == 0x401000


def test_global_variable_object_is_target_matches_obj_ea() -> None:
    """is_target matches cot_obj with matching obj_ea."""
    obj = GlobalVariableObject(0x401000)

    cexpr = MagicMock()
    cexpr.op = idaapi.cot_obj
    cexpr.obj_ea = 0x401000
    assert obj.is_target(cexpr) is True

    cexpr.obj_ea = 0x402000
    assert obj.is_target(cexpr) is False


# --- CallArgObject ------------------------------------------------------------


def test_call_arg_object_init() -> None:
    """CallArgObject captures func_ea + arg_idx."""
    obj = CallArgObject(0x401000, 2)
    assert obj.id == SO_CALL_ARGUMENT
    assert obj.func_ea == 0x401000
    assert obj.arg_idx == 2


def test_call_arg_object_is_target_matches_call_to_func() -> None:
    """is_target matches cot_call whose .x.obj_ea equals func_ea."""
    obj = CallArgObject(0x401000, 0)

    cexpr = MagicMock()
    cexpr.op = idaapi.cot_call
    cexpr.x.obj_ea = 0x401000
    assert obj.is_target(cexpr) is True

    cexpr.x.obj_ea = 0x402000
    assert obj.is_target(cexpr) is False


def test_call_arg_object_create_from_function() -> None:
    """``CallArgObject.create(cfunc, arg_idx)`` reads lvar name + cfunc type."""
    cfunc = MagicMock()
    cfunc.entry_ea = 0x401000
    cfunc.type = "my_t"
    lvar = MagicMock()
    lvar.name = "arg0"
    cfunc.get_lvars.return_value = [lvar]

    obj = CallArgObject.create(cfunc, 0)
    assert obj.func_ea == 0x401000
    assert obj.arg_idx == 0
    assert obj.name == "arg0"
    assert obj.tinfo == "my_t"


# --- ReturnedObject -----------------------------------------------------------


def test_returned_object_init_and_match() -> None:
    """ReturnedObject matches the return value of a specific function."""
    obj = ReturnedObject(0x401000)
    assert obj.id == SO_RETURNED_OBJECT

    cexpr = MagicMock()
    cexpr.op = idaapi.cot_call
    cexpr.x.obj_ea = 0x401000
    assert obj.is_target(cexpr) is True

    cexpr.x.obj_ea = 0x402000
    assert obj.is_target(cexpr) is False


# --- MemoryAllocationObject ---------------------------------------------------


def test_memory_allocation_object_create_for_malloc() -> None:
    """Factory returns an instance for malloc-style calls."""
    cfunc = MagicMock()
    cexpr = MagicMock()
    cexpr.op = idaapi.cot_call
    cexpr.x.obj_ea = 0x401050  # malloc-like address
    cexpr.a = [MagicMock(op=idaapi.cot_num, numval=MagicMock(return_value=0x40))]
    idaapi.get_short_name = MagicMock(return_value="malloc")

    obj = MemoryAllocationObject.create(cfunc, cexpr)
    assert obj is not None
    assert obj.id == SO_MEMORY_ALLOCATOR
    assert obj.name == "malloc"
    assert obj.size == 0x40


def test_memory_allocation_object_create_for_operator_new() -> None:
    """Factory returns an instance for operator new."""
    cfunc = MagicMock()
    cexpr = MagicMock()
    cexpr.op = idaapi.cot_call
    cexpr.x.obj_ea = 0x401060
    cexpr.a = [MagicMock(op=idaapi.cot_num, numval=MagicMock(return_value=0x80))]
    idaapi.get_short_name = MagicMock(return_value="operator new")

    obj = MemoryAllocationObject.create(cfunc, cexpr)
    assert obj is not None
    assert obj.name == "operator new"
    assert obj.size == 0x80


def test_memory_allocation_object_create_for_unknown_call() -> None:
    """Factory returns None for non-allocating calls."""
    cfunc = MagicMock()
    cexpr = MagicMock()
    cexpr.op = idaapi.cot_call
    cexpr.x.obj_ea = 0x401070
    idaapi.get_short_name = MagicMock(return_value="printf")

    obj = MemoryAllocationObject.create(cfunc, cexpr)
    assert obj is None


def test_memory_allocation_object_create_for_non_call() -> None:
    """Factory returns None for non-call expressions."""
    cfunc = MagicMock()
    cexpr = MagicMock()
    cexpr.op = idaapi.cot_num

    obj = MemoryAllocationObject.create(cfunc, cexpr)
    assert obj is None


# --- ScanObject.create factory -----------------------------------------------


def test_scan_object_create_for_var_expr() -> None:
    """Factory returns VariableObject for cot_var cexprs."""
    cfunc = MagicMock()
    cexpr = MagicMock()
    cexpr.op = idaapi.cot_var
    cexpr.v.idx = 3
    cexpr.ea = 0x401000
    lvar = MagicMock()
    lvar.name = "v3"
    lvar.type.return_value = "v3_t"
    cfunc.get_lvars.return_value = [None, None, None, lvar]

    obj = ScanObject.create(cfunc, cexpr)
    assert isinstance(obj, VariableObject)
    assert obj.index == 3
    assert obj.name == "v3"


def test_scan_object_create_for_memptr_expr() -> None:
    """Factory returns StructPtrObject for cot_memptr cexprs."""
    cfunc = MagicMock()
    cexpr = MagicMock()
    cexpr.op = idaapi.cot_memptr
    cexpr.m = 0x10
    cexpr.ea = 0x401000
    cexpr.type = "int"
    cexpr.x.type.get_pointed_object.return_value.dstr.return_value = "Foo"

    obj = ScanObject.create(cfunc, cexpr)
    assert isinstance(obj, StructPtrObject)
    assert obj.struct_name == "Foo"
    assert obj.offset == 0x10


def test_scan_object_create_for_memref_expr() -> None:
    """Factory returns StructRefObject for cot_memref cexprs."""
    cfunc = MagicMock()
    cexpr = MagicMock()
    cexpr.op = idaapi.cot_memref
    cexpr.m = 0x8
    cexpr.ea = 0x401000
    cexpr.type = "int"
    cexpr.x.type.dstr.return_value = "Foo"

    obj = ScanObject.create(cfunc, cexpr)
    assert isinstance(obj, StructRefObject)


def test_scan_object_create_for_obj_expr() -> None:
    """Factory returns GlobalVariableObject for cot_obj cexprs."""
    cfunc = MagicMock()
    cexpr = MagicMock()
    cexpr.op = idaapi.cot_obj
    cexpr.obj_ea = 0x405000
    cexpr.ea = 0x405000
    cexpr.type = "int"
    idaapi.get_short_name = MagicMock(return_value="g_var")

    obj = ScanObject.create(cfunc, cexpr)
    assert isinstance(obj, GlobalVariableObject)
    assert obj.obj_ea == 0x405000
    assert obj.name == "g_var"


def test_scan_object_create_returns_none_for_unsupported_expr() -> None:
    """Factory returns None for expressions not in the dispatch table."""
    cfunc = MagicMock()
    cexpr = MagicMock()
    cexpr.op = idaapi.cot_num
    obj = ScanObject.create(cfunc, cexpr)
    assert obj is None


def test_scan_object_create_for_ctree_item_with_lvar() -> None:
    """Factory handles ctree_item_t input carrying a local var."""
    cfunc = MagicMock()
    lvar = MagicMock()
    lvar.name = "v1"
    lvar.type.return_value = "v1_t"

    item = MagicMock(spec=idaapi.ctree_item_t)
    item.get_lvar.return_value = lvar
    item.citype = idaapi.VDI_EXPR
    item.e = MagicMock()
    item.e.ea = 0x401000

    cfunc.get_lvars.return_value = [lvar]

    obj = ScanObject.create(cfunc, item)
    assert isinstance(obj, VariableObject)
    assert obj.index == 0
    assert obj.name == "v1"


def test_scan_object_create_for_ctree_item_with_expr() -> None:
    """Factory handles ctree_item_t input carrying an expression (not lvar)."""
    cfunc = MagicMock()
    cexpr = MagicMock()
    cexpr.op = idaapi.cot_obj
    cexpr.obj_ea = 0x405000
    cexpr.ea = 0x405000
    cexpr.type = "int"
    idaapi.get_short_name = MagicMock(return_value="g_var")

    item = MagicMock(spec=idaapi.ctree_item_t)
    item.get_lvar.return_value = None
    item.citype = idaapi.VDI_EXPR
    item.e = cexpr

    obj = ScanObject.create(cfunc, item)
    assert isinstance(obj, GlobalVariableObject)
