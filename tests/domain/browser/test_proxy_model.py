"""Test ProxyModel with Qt offscreen."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock, patch

from hexrays_pytools.domain.browser.proxy_model import ProxyModel


def test_proxy_model_init() -> None:
    m = ProxyModel()
    assert m.filter_by_function is False


def test_set_regexp_filter_class_name() -> None:
    m = ProxyModel()
    m.set_regexp_filter("Foo")
    assert m.filter_by_function is False


def test_set_regexp_filter_function_with_bang() -> None:
    """Prefix '!' switches to function-name filter mode."""
    m = ProxyModel()
    m.set_regexp_filter("!doSomething")
    assert m.filter_by_function is True


def test_set_regexp_filter_empty() -> None:
    m = ProxyModel()
    m.set_regexp_filter("")
    assert m.filter_by_function is False


def test_set_regexp_filter_invalid_falls_back_to_noop() -> None:
    """Invalid regex pattern doesn't crash; filter becomes no-op."""
    m = ProxyModel()
    m.set_regexp_filter("[invalid")  # unmatched bracket
    # Filter should still work (just not filter anything out)
    assert m._compile_error != "" or m.filterRegularExpression().pattern() == ""


def test_filter_accepts_row_no_pattern() -> None:
    """With no pattern set, all rows are accepted."""
    m = ProxyModel()
    parent = MagicMock()
    assert m.filterAcceptsRow(0, parent) is True


def test_filter_accepts_row_matches_name() -> None:
    """A name matching the regex is accepted."""
    m = ProxyModel()
    m.set_regexp_filter("Foo")
    # Build a fake source index with internalPointer returning a node
    src = MagicMock()
    node = MagicMock()
    node.name = "FooBar"
    item = MagicMock()
    item.item = node
    idx = MagicMock()
    idx.isValid.return_value = True
    idx.internalPointer.return_value = item
    src.index.return_value = idx
    # setSourceModel() rejects non-QAbstractItemModel args at the binding
    # level; patch it so we can drive filterAcceptsRow with a mock source.
    with patch.object(m, "sourceModel", return_value=src):
        assert m.filterAcceptsRow(0, MagicMock()) is True


def test_filter_accepts_row_non_match() -> None:
    """A name not matching the regex is rejected."""
    m = ProxyModel()
    m.set_regexp_filter("Foo")
    src = MagicMock()
    node = MagicMock()
    node.name = "BarBaz"
    item = MagicMock()
    item.item = node
    idx = MagicMock()
    idx.isValid.return_value = True
    idx.internalPointer.return_value = item
    src.index.return_value = idx
    with patch.object(m, "sourceModel", return_value=src):
        assert m.filterAcceptsRow(0, MagicMock()) is False


def test_filter_accepts_row_by_function() -> None:
    """'!' prefix routes to node.has_function."""
    m = ProxyModel()
    m.set_regexp_filter("!doSomething")
    src = MagicMock()
    node = MagicMock()
    node.name = "Foo"
    node.has_function.return_value = True
    item = MagicMock()
    item.item = node
    idx = MagicMock()
    idx.isValid.return_value = True
    idx.internalPointer.return_value = item
    src.index.return_value = idx
    with patch.object(m, "sourceModel", return_value=src):
        assert m.filterAcceptsRow(0, MagicMock()) is True
    node.has_function.assert_called_once_with("doSomething")
