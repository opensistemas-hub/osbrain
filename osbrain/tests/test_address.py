import zmq
import pytest

from osbrain.address import AgentAddress
from osbrain.address import SocketAddress
from osbrain.address import AgentAddressKind
from osbrain.address import AgentAddressRole


def twin_list(elements):
    result = elements[:]
    result[1::2] = elements[::2]
    result[::2] = elements[1::2]
    return result


def test_kind():
    """
    This test aims to cover basic AgentAddressKind operations: initialization,
    equivalence and basic methods.
    """
    strings = ['REQ', 'REP', 'PUSH', 'PULL', 'PUB', 'SUB']
    zmqints = [zmq.REQ, zmq.REP, zmq.PUSH, zmq.PULL, zmq.PUB, zmq.SUB]
    handlers = [False, True, False, True, False, True]
    strtwins = twin_list(strings)
    zmqtwins = twin_list(zmqints)
    configurations = zip(strings, strtwins, zmqints, zmqtwins, handlers)
    # Make sure there are no missing values
    assert len(list(configurations)) == len(strings)

    for string, strtwin, zmqint, zmqtwin, handler in configurations:
        # Initialization and equivalence
        kind = AgentAddressKind(string)
        assert kind == zmqint
        assert kind == string
        assert kind == AgentAddressKind(zmqint)
        assert kind == AgentAddressKind(kind)
        # Basic methods
        assert isinstance(kind.twin(), AgentAddressKind)
        assert kind.twin() == strtwin
        assert kind.requires_handler() == handler
    # Value error exceptions
    with pytest.raises(ValueError):
        AgentAddressKind('FOO')


def test_role():
    """
    This test aims to cover basic AgentAddressRole operations: initialization,
    equivalence and basic methods.
    """
    values = ['server', 'client']
    twins = twin_list(values)
    for value, twin in zip(values, twins):
        # Initialization and equivalence
        role = AgentAddressRole(value)
        assert role == value
        assert role == AgentAddressRole(role)
        # Basic methods
        assert isinstance(role.twin(), AgentAddressRole)
        assert role.twin() == twin
    # Value error exceptions
    with pytest.raises(ValueError):
        AgentAddressRole('foo')
    with pytest.raises(ValueError):
        AgentAddressRole(1)


def test_socket_address():
    """
    Test basic SocketAddress operations: initialization and equivalence.
    """
    address = SocketAddress('127.0.0.1', 1234)
    # Equivalence
    assert address == SocketAddress('127.0.0.1', 1234)
    assert address != SocketAddress('127.0.0.0', 1234)
    assert address != SocketAddress('127.0.0.1', 1230)
    assert not address == 'foo'
    assert address != 'foo'


def test_agent_address():
    """
    Test basic AgentAddress operations: initialization, equivalence and
    basic methods.
    """
    address = AgentAddress('127.0.0.1', 1234, 'PUSH', 'server')
    # Equivalence
    assert address == AgentAddress('127.0.0.1', 1234, 'PUSH', 'server')
    assert not address == 'foo'
    assert address != 'foo'
    # Basic methods
    assert address.socket_addr() == SocketAddress('127.0.0.1', 1234)
    assert address.twin() == AgentAddress('127.0.0.1', 1234, 'PULL', 'client')
