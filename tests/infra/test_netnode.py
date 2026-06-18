"""Test Netnode wrapper."""
from hexrays_pytools.infra.idb.netnode import Netnode


def test_netnode_creates_with_name() -> None:
    """Netnode(name) creates a netnode via idaapi.netnode(name)."""
    Netnode("$test_name")
    idaapi = __import__("idaapi")
    idaapi.netnode.assert_called_with("$test_name")


def test_netnode_exists_property() -> None:
    """exists property returns True if node value is not 0."""
    __import__("idaapi").netnode.return_value = 42
    netnode = Netnode("$test")
    assert netnode.exists is True


def test_netnode_get_string_returns_empty_when_none() -> None:
    """get_string() returns empty string if supstr returns None."""
    __import__("idaapi").netnode.return_value.supstr.return_value = None
    netnode = Netnode("$test")
    assert netnode.get_string() == ""


def test_netnode_set_string_calls_supset() -> None:
    """set_string calls node.supset with the value."""
    __import__("idaapi").netnode.return_value.supset.return_value = True
    netnode = Netnode("$test")
    result = netnode.set_string("hello world")
    __import__("idaapi").netnode.return_value.supset.assert_called_with(0, "hello world")
    assert result is True


def test_netnode_delete_calls_kill() -> None:
    """delete() calls node.kill() and returns its result."""
    mock_node = __import__("idaapi").netnode.return_value
    mock_node.kill.return_value = True
    netnode = Netnode("$test")
    assert netnode.delete() is True
    mock_node.kill.assert_called_once()
