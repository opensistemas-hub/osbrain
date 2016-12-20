"""
Proxy module tests.
"""
import time

import pytest

from osbrain import run_agent
from osbrain import Proxy
from osbrain.proxy import locate_ns

from common import nsproxy  # pragma: no flakes


def test_wrong_nameserver_address():
    """
    Locating a name server that does not exist should raise an error.
    """
    with pytest.raises(TimeoutError):
        locate_ns('127.0.0.1:22', timeout=1.)


def test_proxy_without_nsaddr(nsproxy):
    """
    Creating a proxy without specifying the name server address should
    result in the OSBRAIN_NAMESERVER_ADDRESS being used.
    """
    agent0 = run_agent('foo')
    agent0.set_attr(x=1.)
    agent1 = Proxy('foo')
    assert agent1.get_attr('x') == 1.


def test_agent_proxy_remote_exceptions(nsproxy):
    """
    Remote exceptions on method executions should be raised locally by the
    proxy with information on what did go wrong remotely.
    """
    agent = run_agent('a0')
    with pytest.raises(TypeError) as error:
        agent.addr('asdf', 'qwer', 'foo', 'bar')
        assert 'positional arguments but 5 were given' in str(error.value)
    with pytest.raises(RuntimeError) as error:
        agent.raise_exception()
        assert 'User raised an exception' in str(error.value)


def test_initialization_timeout(nsproxy):
    """
    A proxy should raise a TimeoutError at initialization if it can not test
    the connection within a number of seconds.
    """
    class TestTimeoutProxy(Proxy):
        def test(self):
            time.sleep(0.1)
            raise TimeoutError()

    run_agent('foo')
    with pytest.raises(TimeoutError):
        TestTimeoutProxy('foo', timeout=1.)
