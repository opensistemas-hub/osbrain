import pytest

from osbrain.address import AgentAddress
from osbrain.address import SocketAddress
from osbrain.common import LogLevel
from osbrain.common import address_to_host_port


def test_loglevel():
    """
    Test LogLevel class initialization.
    """
    # Valid initialization
    for level in ['ERROR', 'WARNING', 'INFO', 'DEBUG']:
        LogLevel(level)
    # Invalid initialization
    with pytest.raises(ValueError):
        LogLevel('FOO')


class DummyAddress():
    """
    A dummy class which has `host` and `port` attributes set.
    """
    host = '127.0.0.1'
    port = 1234


class DummyAddressMethod():
    """
    A dummy class which has an `addr` method that returns a dummy address.
    """
    def addr(self):
        return DummyAddress()


@pytest.mark.parametrize(('address', 'host', 'port'), [
    (None, None, None),
    (AgentAddress('127.0.0.1', 1234, 'PUSH', 'server'), '127.0.0.1', 1234),
    (SocketAddress('127.0.0.1', 1234), '127.0.0.1', 1234),
    ('127.0.0.1:1234', '127.0.0.1', 1234),
    ('127.0.0.1', '127.0.0.1', None),
    (DummyAddress(), '127.0.0.1', 1234),
    (DummyAddressMethod(), '127.0.0.1', 1234),
])
def test_valid_address_to_host_port(address, host, port):
    """
    Test conversion of an address to its corresponding host+port tuple.
    """
    assert address_to_host_port(address) == (host, port)


def test_invalid_address_to_host_port():
    """
    Test conversion of a wrong type to its corresponding host+port tuple.
    This conversion should cause an exception raising.
    """
    with pytest.raises(ValueError):
        address_to_host_port(1.234)
