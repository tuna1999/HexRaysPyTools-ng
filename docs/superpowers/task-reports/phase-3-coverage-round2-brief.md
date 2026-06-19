# Phase 3 coverage round 2: add tests for plugin, main, and widget data methods

## Context

Phase 3 coverage still at 76.76%, need ≥80%. The remaining gap is mostly:
- plugin.py: 0% (entry point)
- __main__.py: 0% (entry)
- registered_class.py: 54% (Class.create not tested)
- tree_model.py: 45% (data + setupModelData not tested)
- structure_model.py: 67% (data not tested)
- type_library.py: 72% (create_type, import_type paths not covered)

## Files to Create/Modify

### 1. tests/test_plugin.py (new)

```python
"""Test plugin.py and __main__.py entry points."""
from hexrays_pytools.__main__ import PLUGIN_ENTRY
from hexrays_pytools.plugin import HexRaysPyToolsPlugin


def test_plugin_entry_is_class() -> None:
    """PLUGIN_ENTRY is the HexRaysPyToolsPlugin class."""
    assert PLUGIN_ENTRY is HexRaysPyToolsPlugin


def test_plugin_class_has_required_attributes() -> None:
    """Plugin has flags, comment, help, wanted_name, wanted_hotkey."""
    assert hasattr(HexRaysPyToolsPlugin, "flags")
    assert hasattr(HexRaysPyToolsPlugin, "wanted_name")
    assert HexRaysPyToolsPlugin.wanted_name == "HexRaysPyTools"
    assert HexRaysPyToolsPlugin.wanted_hotkey == ""


def test_plugin_run_no_op() -> None:
    """run() takes args and does nothing."""
    HexRaysPyToolsPlugin.run()  # should not raise
    HexRaysPyToolsPlugin.run(1, 2, 3)  # should not raise


def test_plugin_term_without_session() -> None:
    """term() handles missing session gracefully."""
    HexRaysPyToolsPlugin.session = None
    HexRaysPyToolsPlugin.term()  # should not raise
```

### 2. tests/domain/browser/test_registered_class.py (modify)

Add new tests to existing file:

```python
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
    idaapi.get_numbered_type.return_value = True
    result = Class.create(42)
    assert result is not None
    assert result.ordinal == 42
    assert result.name == "Foo"


def test_create_class_returns_none_for_non_udt() -> None:
    idaapi = __import__("idaapi")
    tinfo = MagicMock()
    tinfo.is_udt.return_value = False
    idaapi.tinfo_t.return_value = tinfo
    assert Class.create(1) is None


def test_create_class_returns_none_for_no_vtable() -> None:
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
```

### 3. tests/domain/recon/test_structure_model.py (modify)

Add 2 tests:

```python
def test_model_data_display_role() -> None:
    """data() returns correct values for each column."""
    from PySide6 import QtCore
    item = AbstractMember(offset=0x10, name="foo")
    item.tinfo = MagicMock()
    item.tinfo.get_size.return_value = 4
    m = StructureModel(items=[item])
    idx = m.index(0, 0, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.DisplayRole) == "0x10"
    idx = m.index(0, 1, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.DisplayRole) == "foo"
    idx = m.index(0, 2, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.DisplayRole) is not None  # str(tinfo)
    idx = m.index(0, 3, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.DisplayRole) == 4
    idx = m.index(0, 4, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.DisplayRole) is True


def test_model_data_invalid_index() -> None:
    """data() returns None for invalid index."""
    from PySide6 import QtCore
    m = StructureModel()
    invalid_idx = QtCore.QModelIndex()
    assert m.data(invalid_idx, QtCore.Qt.DisplayRole) is None


def test_model_data_non_display_role() -> None:
    """data() returns None for non-DisplayRole."""
    from PySide6 import QtCore
    m = StructureModel(items=[AbstractMember(offset=0, name="x")])
    idx = m.index(0, 0, QtCore.QModelIndex())
    assert m.data(idx, QtCore.Qt.EditRole) is None
```

### 4. tests/domain/til/test_type_library.py (modify)

Add tests:

```python
def test_create_type_returns_false_when_idc_parse_types_fails() -> None:
    """create_type returns False when type creation fails."""
    idaapi = __import__("idaapi")
    tif = MagicMock()
    tif.get_named_type.return_value = False  # both calls return False
    idaapi.tinfo_t.return_value = tif
    assert create_type("NewType", "struct NewType { int x; };") is False
```

## Verification

```bash
PYTHONPATH=src pytest tests/ --no-cov  # all 150+ tests pass
python -m mypy --strict src/hexrays_pytools/  # clean
python -m ruff check src/hexrays_pytools/ tests/ tools/  # clean
PYTHONPATH=src pytest  # full suite with coverage
```

The coverage should be ≥80%.

## Commit

```bash
git add tests/test_plugin.py tests/domain/browser/test_registered_class.py tests/domain/recon/test_structure_model.py tests/domain/til/test_type_library.py
git commit -m "test: add coverage tests (plugin entry, Class.create, data() methods)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\phase-3-coverage-round2-report.md`