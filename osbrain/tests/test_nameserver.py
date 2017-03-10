"""
Test file for nameserver.
"""
import os
import time
import random
from threading import Timer

import pytest

from osbrain import SocketAddress
from osbrain import run_agent
from osbrain import run_nameserver
from osbrain import Agent
from osbrain import NSProxy
from osbrain.nameserver import NameServerProcess
from osbrain.nameserver import random_nameserver_process

from common import nsaddr  # pragma: no flakes
from common import nsproxy  # pragma: no flakes


def test_nameserver_ping(nsproxy):
    """
    Simple name server ping test.
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
    Shutdown a name server from a name server proxy.
    """
    ns = run_nameserver()
    run_agent('Agent0', nsaddr=ns.addr())
    run_agent('Agent1', nsaddr=ns.addr())
    ns.shutdown()


def test_nameserverprocess_shutdown():
    """
    Name server shutdown can be called directly from the name server process.
    """
    nameserver = random_nameserver_process()
    run_agent('a0')
    run_agent('a1')
    while not len(nameserver.agents()) == 2:
        continue
    assert 'a0' in nameserver.agents()
    assert 'a1' in nameserver.agents()
    nameserver.shutdown()
    assert not nameserver.is_alive()


def test_nameserverprocess_shutdown_lazy_agents():
    """
    Shutdown a name server process with agents that wait some time before
    shutting down.
    """
    class Lazy(Agent):
        def shutdown(self):
            time.sleep(1)
            super().shutdown()

    nsprocess = random_nameserver_process()
    run_agent('a0', base=Lazy)
    run_agent('a1', base=Lazy)

    t0 = time.time()
    nsprocess.shutdown()
    assert time.time() - t0 > 2


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


def test_nameserver_process_default_host():
    """
    A name server process should default to localhost (127.0.0.1).
    """
    ns = NameServerProcess(1234)
    assert ns.port == 1234
    assert ns.host == '127.0.0.1'


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


def test_random_nameserver_process():
    """
    Basic random_nameserver_process function tests: port range and exceptions.
    """
    # Port range
    port_start = 11000
    port_stop = port_start + 100
    nsprocess = random_nameserver_process(port_start=port_start,
                                          port_stop=port_stop)
    address = nsprocess.addr
    assert port_start <= address.port <= port_stop
    ns = NSProxy(address)
    ns.shutdown()
    # Raising exceptions
    with pytest.raises(ValueError):
        random_nameserver_process(port_start=-1, port_stop=-2)
    with pytest.raises(RuntimeError):
        random_nameserver_process(port_start=22, port_stop=22, timeout=0.5)


def test_nameserver_oserror(nsaddr):
    """
    Name server start() should raise an error if address is already in use.
    """
    with pytest.raises(RuntimeError) as error:
        run_nameserver(nsaddr)
    assert 'OSError' in str(error.value)
    assert 'Address already in use' in str(error.value)


def test_nameserver_permissionerror():
    """
    Name server start() should raise an error if it has not sufficient
    permissions.
    """
    with pytest.raises(RuntimeError) as error:
        run_nameserver('127.0.0.1:22')
    assert 'PermissionError' in str(error.value)
    assert 'Permission denied' in str(error.value)
