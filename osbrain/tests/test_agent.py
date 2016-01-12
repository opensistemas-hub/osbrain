import pytest
import random
from Pyro4.errors import NamingError
from osbrain.core import Agent
from osbrain.core import Proxy
from osbrain.core import NSProxy
from osbrain.core import NameServer
from osbrain.core import SocketAddress


@pytest.fixture(scope='function')
def nsaddr(request):
    while True:
        try:
            # Bind to random port
            host = '127.0.0.1'
            port = random.randrange(10000, 20000)
            addr = SocketAddress(host, port)
            ns = NameServer(addr)
            ns.start()
            def terminate():
                print('addfinalizer...')
                ns.kill()
            request.addfinalizer(terminate)
            return addr
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
    assert agents[name] == 'PYRO:%s@%s' % (name, nsaddr)


def test_registration(nsaddr):
    """
    Verify new agents get registered in the nameserver.
    """
    Agent('a0', nsaddr=nsaddr).start()
    Agent('a1', nsaddr=nsaddr).start()
    agent_list = NSProxy(nsaddr).list()
    assert 'a0' in agent_list
    assert 'a1' in agent_list
    # TODO: automatically kill all agents registered in the nameserver
    Proxy('a0', nsaddr=nsaddr).kill()
    Proxy('a1', nsaddr=nsaddr).kill()


def test_agent_loopback(nsaddr):
    """
    An agent should always have a loopback inproc socket.
    """
    Agent('a0', nsaddr=nsaddr).start()
    addr = Proxy('a0', nsaddr=nsaddr).get_addr('loopback')
    assert addr == 'inproc://loopback'
    # TODO: automatically kill all agents registered in the nameserver
    Proxy('a0', nsaddr=nsaddr).kill()
