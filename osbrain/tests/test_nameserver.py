"""
Test file for nameserver.
"""
import os
import random
from threading import Timer
from osbrain.nameserver import NameServerProcess
from osbrain.address import SocketAddress
from osbrain import run_agent
from osbrain import run_nameserver
from osbrain import NSProxy

from common import nsaddr  # pragma: no flakes
from common import nsproxy  # pragma: no flakes


def test_nameserver_ping(nsproxy):
    """
    Ping name server.
    """
    assert nsproxy.ping() == 'pong'


def test_nameserver_list(nsproxy):
    """
    A simple test that checks the correct creation of a name server.
    """
    agents = nsproxy.list()
    name = 'Pyro.NameServer'
    assert len(agents) == 1
    assert list(agents.keys())[0] == name
    assert agents[name] == 'PYRO:%s@%s' % (name, nsproxy.addr())


def test_nameserver_proxy_list(nsaddr):
    """
    Verify new agents get registered in the nameserver.
    """
    run_agent('a0', nsaddr)
    run_agent('a1', nsaddr)
    # List registered agents
    agent_list = NSProxy(nsaddr).list()
    assert 'a0' in agent_list
    assert 'a1' in agent_list


def test_nameserver_proxy_shutdown_no_agents():
    """
    Shutdown a name server through a proxy when the name server has no
    agents registered.
    """
    ns = run_nameserver()
    ns.shutdown()


def test_nameserver_proxy_shutdown_agents(nsproxy):
    """
    Shutdown agents registered in a name server from a name server proxy.
    """
    run_agent('Agent0', nsaddr=nsproxy.addr())
    run_agent('Agent1', nsaddr=nsproxy.addr())
    nsproxy.shutdown_agents()
    assert len(nsproxy.agents()) == 0


def test_nameserver_proxy_shutdown_with_agents():
    """
    Shutdown agents registered in a name server from a name server proxy.
    """
    ns = run_nameserver()
    run_agent('Agent0', nsaddr=ns.addr())
    run_agent('Agent1', nsaddr=ns.addr())
    ns.shutdown()


def test_nameserver_proxy_timeout():
    """
    When creating a proxy to the name server, there should be a timeout
    before raising an error if the name server cannot be located.
    """
    while True:
        try:
            # Bind to random port
            host = '127.0.0.1'
            port = random.randrange(10000, 20000)
            addr = SocketAddress(host, port)
            nameserver = NameServerProcess(addr)
            # Start name server later
            Timer(1, nameserver.start).start()
            # Locate name server now
            pyro_address = NSProxy(addr, timeout=3.).addr()
        except PermissionError:
            continue
        break
    assert pyro_address.host == host
    assert pyro_address.port == port
    nameserver.shutdown()


def test_nameserver_environ(nsproxy):
    """
    When starting a nameserver, a environment variable should be set to ease
    the process of running new agents.
    """
    assert str(nsproxy.addr()) == os.environ.get('OSBRAIN_NAMESERVER_ADDRESS')
    run_agent('a0')
    run_agent('a1')
    # List registered agents
    agent_list = nsproxy.list()
    assert 'a0' in agent_list
    assert 'a1' in agent_list


def test_nameserver_agents(nsproxy):
    """
    Test the agents() method, which should return a list with the names of
    the registered agents.
    """
    # No agents registered
    agents = nsproxy.agents()
    assert len(agents) == 0
    # One agent registered
    run_agent('Agent0')
    agents = nsproxy.agents()
    assert len(agents) == 1
    # Two agents registered
    run_agent('Agent1')
    agents = nsproxy.agents()
    assert len(agents) == 2
    assert 'Agent0' in agents
    assert 'Agent1' in agents


def test_nameserver_agent_address(nsproxy):
    """
    A name server proxy can be used to retrieve an agent's socket address as
    well, given the agent's alias and the socket's alias.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    addr0 = a0.bind('PUB', alias='foo')
    addr1 = a1.bind('PUSH', alias='bar')
    assert nsproxy.addr('a0', 'foo') == addr0
    assert nsproxy.addr('a1', 'bar') == addr1
