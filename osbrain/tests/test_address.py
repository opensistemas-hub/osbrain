"""
Test file for address module.
"""
from collections import namedtuple

import zmq
import pytest

from osbrain.address import address_to_host_port
from osbrain.address import guess_kind
from osbrain.address import SocketAddress
from osbrain.address import AgentAddress
from osbrain.address import AgentAddressKind
from osbrain.address import AgentAddressRole
from osbrain.address import AgentAddressTransport
from osbrain.address import AgentAddressSerializer
from osbrain.address import AgentChannel
from osbrain.address import AgentChannelKind


def twin_list(elements):
    result = elements[:]
    result[1::2] = elements[::2]
    result[::2] = elements[1::2]
    return result


def test_invalid_address_to_host_port():
    """
    Test conversion of a wrong type to its corresponding host+port tuple.
    This conversion should cause an exception raising.
    """
    with pytest.raises(ValueError):
        address_to_host_port(1.234)


@pytest.mark.parametrize(('address', 'host', 'port'), [
    (None, None, None),
    (AgentAddress('tcp', '127.0.0.1:123', 'PUSH', 'server', 'pickle'),
     '127.0.0.1', 123),
    (SocketAddress('127.0.0.1', 123), '127.0.0.1', 123),
    ('127.0.0.1:123', '127.0.0.1', 123),
    ('127.0.0.1', '127.0.0.1', None),
    (namedtuple('Foo', ['host', 'port'])('127.0.0.1', 123), '127.0.0.1', 123),
])
def test_valid_address_to_host_port(address, host, port):
    """
    Test conversion of an address to its corresponding host+port tuple.
    """
    assert address_to_host_port(address) == (host, port)


@pytest.mark.parametrize('kind,cls', [
    ('PUB', AgentAddressKind),
    ('REQ', AgentAddressKind),
    ('PUSH', AgentAddressKind),
    ('ASYNC_REP', AgentChannelKind),
    ('SYNC_PUB', AgentChannelKind),
])
def test_guess_kind(kind, cls):
    """
    Test guessing address/channel kind.
    """
    guessed = guess_kind(kind)
    assert guessed == kind
    assert isinstance(guessed, cls)


def test_transport():
    """
    This test aims to cover basic AgentAddressTransport initialization and
    equivalence.
    """
    assert AgentAddressTransport('tcp') == 'tcp'
    assert AgentAddressTransport('ipc') == 'ipc'
    assert AgentAddressTransport('inproc') == 'inproc'
    with pytest.raises(ValueError):
        AgentAddressTransport('foo')


@pytest.mark.parametrize('string,strtwin,zmqint,zmqtwin,handler', [
    ('REQ', 'REP', zmq.REQ, zmq.REP, False),
    ('REP', 'REQ', zmq.REP, zmq.REQ, True),
    ('PUSH', 'PULL', zmq.PUSH, zmq.PULL, False),
    ('PULL', 'PUSH', zmq.PULL, zmq.PUSH, True),
    ('PUB', 'SUB', zmq.PUB, zmq.SUB, False),
    ('SUB', 'PUB', zmq.SUB, zmq.PUB, True),
])
def test_kind(string, strtwin, zmqint, zmqtwin, handler):
    """
    This test aims to cover basic AgentAddressKind operations: initialization,
    equivalence and basic methods.
    """
    # Initialization and equivalence
    kind = AgentAddressKind(string)
    assert kind == string
    assert kind == AgentAddressKind(kind)
    # Basic methods
    assert kind.zmq() == zmqint
    assert isinstance(kind.twin(), AgentAddressKind)
    assert kind.twin() == strtwin
    assert kind.requires_handler() == handler


def test_kind_value_error():
    """
    Creating an AgentAddressKind with a wrong value should result in an
    exception being raised.
    """
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


def test_serializer():
    """
    This test aims to cover basic AgentAddressSerializer initialization and
    equivalence.
    """
    assert AgentAddressSerializer('raw') == 'raw'
    assert AgentAddressSerializer('pickle') == 'pickle'
    assert AgentAddressSerializer('json') == 'json'
    with pytest.raises(ValueError):
        AgentAddressSerializer('foo')


def test_serializer_separator():
    """
    Check which serializers do require a separator between topic and
    message to be automatically inserted.
    """
    assert not AgentAddressSerializer('raw').requires_separator
    assert AgentAddressSerializer('pickle').requires_separator
    assert AgentAddressSerializer('json').requires_separator


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
    address = AgentAddress('ipc', 'addr', 'PUSH', 'server', 'pickle')
    # Equivalence
    assert address == AgentAddress('ipc', 'addr', 'PUSH', 'server', 'pickle')
    assert not address == 'foo'
    assert address != 'foo'
    # Basic methods
    assert address.twin() == AgentAddress('ipc', 'addr', 'PULL', 'client',
                                          'pickle')


def test_agent_address_explicit_serializer():
    """
    Test basic AgentAddress operations: initialization, equivalence and
    basic methods when an explicit serializer is used.
    """
    address = AgentAddress('ipc', 'addr', 'PUSH', 'server', 'raw')
    # Equivalence
    assert address == AgentAddress('ipc', 'addr', 'PUSH', 'server', 'raw')
    assert not address == 'foo'
    assert address != 'foo'
    # Basic methods
    assert address.twin() == AgentAddress('ipc', 'addr', 'PULL', 'client',
                                          'raw')
    assert address.twin() != AgentAddress('ipc', 'addr', 'PULL', 'client',
                                          'pickle')


def test_agent_address_to_host_port():
    """
    An agent address should be convertible to host+port if TCP is used.
    """
    address = AgentAddress('tcp', '127.0.0.1:1234', 'PUSH', 'server', 'pickle')
    assert address_to_host_port(address) == ('127.0.0.1', 1234)


@pytest.mark.parametrize('string,string_twin', [
    ('ASYNC_REQ', 'ASYNC_REP'),
    ('ASYNC_REP', 'ASYNC_REQ'),
    ('SYNC_PUB', 'SYNC_SUB'),
    ('SYNC_SUB', 'SYNC_PUB'),
])
def test_agentchannelkind(string, string_twin):
    """
    This test aims to cover basic AgentChannelKind operations: initialization,
    equivalence and basic methods.
    """
    # Initialization and equivalence
    kind = AgentChannelKind(string)
    assert kind == string
    assert kind == AgentChannelKind(kind)
    # Basic methods
    assert isinstance(kind.twin(), AgentChannelKind)
    assert kind.twin() == string_twin


def test_agentchannelkind_value_error():
    """
    Creating an AgentChannelKind with a wrong value should result in an
    exception being raised.
    """
    # Value error exceptions
    with pytest.raises(ValueError):
        AgentChannelKind('FOO')


def test_agentchannel():
    """
    Test basic AgentChannel operations: initialization, equivalence and
    basic methods.
    """
    address0 = AgentAddress('ipc', 'addr0', 'PULL', 'server', 'pickle')
    address1 = None
    channel = AgentChannel('ASYNC_REP', address0, address1)
    # Equivalence
    assert channel == AgentChannel('ASYNC_REP', address0, address1)
    assert not channel == 'foo'
    assert channel != 'foo'
    # Basic methods
    assert channel.twin() == AgentChannel('ASYNC_REQ', address0.twin(), None)
