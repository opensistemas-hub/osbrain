import pytest
import random
from Pyro4.errors import NamingError
from osbrain.core import Proxy
from osbrain.core import NSProxy
from osbrain.core import NameServer


@pytest.fixture(scope='function')
def nsaddr(request):
    while True:
        try:
            # Bind to random port
            ns = NameServer('127.0.0.1:0')
            ns.start()
            def terminate():
                ns.terminate()
                ns.join()
            request.addfinalizer(terminate)
            return ns.addr
        except NamingError:
            continue
        except PermissionError:
            continue


def test_nameserver(nsaddr):
    """
    A simple test that checks the correct creation of a name server.
    """
    nsproxy = NSProxy(nsaddr)
    agents = nsproxy.list()
    name = 'Pyro.NameServer'
    assert len(agents) == 1
    assert list(agents.keys())[0] == name
    assert agents[name] == 'PYRO:%s@%s' % (name, nsaddr.socket_addr())
