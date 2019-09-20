"""
Test file for nameserver.
"""
import multiprocessing
import os
import random
import time
from threading import Timer

import pytest

from osbrain import Agent
from osbrain import AgentProcess
from osbrain import NameServer
from osbrain import NSProxy
from osbrain import Proxy
from osbrain import SocketAddress
from osbrain import run_agent
from osbrain import run_nameserver
from osbrain.helper import wait_agent_attr
from osbrain.nameserver import NameServerProcess
from osbrain.nameserver import random_nameserver_process

from .common import skip_windows_any_port
from .common import skip_windows_port_reuse


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


def test_nameserver_proxy_list(nsproxy):
    """
    Verify new agents get registered in the nameserver.
    """
    run_agent('a0', nsproxy.addr())
    run_agent('a1', nsproxy.addr())
    # List registered agents
    agent_list = nsproxy.list()
    assert 'a0' in agent_list
    assert 'a1' in agent_list


def test_run_agents_same_name(nsproxy):
    """
    Check that the user cannot create two agents with the same name. A
    RuntimeError should be raised.
    """
    run_agent('name')
    with pytest.raises(RuntimeError) as error:
        run_agent('name')
    assert 'name already registered' in str(error.value)


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


def test_nameserver_proxy_shutdown_with_many_agents():
    """
    Shutdown a name server from a name server proxy when there are many agents
    registered in the name server (make sure proxies do not saturate the name
    server on shutdown).

    The shutdown process is given a long timeout to avoid raising exceptions.
    """
    import Pyro4

    Pyro4.config.THREADPOOL_SIZE = 4
    ns = run_nameserver()
    for i in range(20):
        run_agent('Agent%s' % i)
    ns.shutdown(timeout=60)


def test_nameserver_proxy_shutdown_with_many_agents_timeout():
    """
    Shutdown a name server from a name server proxy when there are many agents
    registered in the name server (make sure proxies do not saturate the name
    server on shutdown).

    The shutdown process is given the shortest timeout to ensure an exception
    is raised.
    """
    import Pyro4

    Pyro4.config.THREADPOOL_SIZE = 4
    ns = run_nameserver()
    for i in range(20):
        run_agent('Agent%s' % i)
    with pytest.raises(TimeoutError):
        ns.shutdown(timeout=0.0)
    ns.shutdown()


@pytest.mark.parametrize('delay', [1, 3, 5])
@pytest.mark.parametrize('timeout', [True, False])
def test_nameserver_proxy_shutdown_lazy_agents(delay, timeout):
    """
    Shutdown a name server proxy with agents that wait some time before
    shutting down.

    The name server shutdown should always succeed. If the agents do not
    shutdown cleanly soon they should be hard-killed.
    """

    class Lazy(Agent):
        def shutdown(self):
            time.sleep(delay)
            super().shutdown()

    ns = run_nameserver()
    run_agent('a0', base=Lazy)
    run_agent('a1', base=Lazy)

    t0 = time.time()
    if timeout:
        ns.shutdown(timeout=10)
    else:
        ns.shutdown()
    assert time.time() - t0 > delay / 2.0
    assert time.time() - t0 < delay + 2


def test_nameserver_proxy_shutdown_raise_timeout():
    """
    A name server proxy should raise a TimeoutError if agents were not shutdown
    or killed before the set timeout.
    """
    ns = run_nameserver()
    run_agent('a0')
    with pytest.raises(TimeoutError) as error:
        ns.shutdown(timeout=0.0)
    assert 'not shutdown after' in str(error.value)
    ns.shutdown()


def test_nameserver_proxy_shutdown_with_pyroerror():
    """
    Check that `PyroError`s raised during `async_nameserver_shutdown` are
    handled correctly.
    """
    nameserver = run_nameserver()
    ap = AgentProcess()
    name = ap.start()
    proxy = Proxy(name)
    proxy.run()

    ap.kill()
    nameserver.async_shutdown_agents(nameserver.addr())
    nameserver.shutdown()


def test_oneway_kill_non_running_agent_on_name_server_shutdown():
    """
    The agent's `shutdown` method is only executed for running agents. When
    agents are not running (i.e.: they raised an exception while running or
    their `keep_alive` attribute was simply set to `False`, the `kill` method
    is called instead.

    When killing a non-running agent (i.e.: when shutting down the
    architecture from the name server), this call is expected to be executed
    one-way, as otherwise the Pyro daemon will shut down before returning
    from the method, resulting in a `ConnectionClosedError`.
    """

    class WilliamWallace(Agent):
        def kill(self):
            super().kill()
            time.sleep(2)

    ns = run_nameserver()
    william = run_agent('william', base=WilliamWallace)
    # Stop the agent
    william.set_attr(_keep_alive=False)
    assert wait_agent_attr(william, name='_running', value=False)
    # Shut down should work just fine
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
    assert time.time() - t0 > 1


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
            pyro_address = NSProxy(addr, timeout=3.0).addr()
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


@skip_windows_any_port
def test_random_nameserver_process():
    """
    Basic random_nameserver_process function tests: port range and exceptions.
    """
    # Port range
    port_start = 11000
    port_stop = port_start + 100
    nsprocess = random_nameserver_process(
        port_start=port_start, port_stop=port_stop
    )
    address = nsprocess.addr
    assert port_start <= address.port <= port_stop
    ns = NSProxy(address)
    ns.shutdown()
    # Raising exceptions
    with pytest.raises(ValueError):
        random_nameserver_process(port_start=-1, port_stop=-2)
    with pytest.raises(RuntimeError):
        random_nameserver_process(port_start=22, port_stop=22, timeout=0.5)


@skip_windows_port_reuse
def test_nameserver_oserror(nsproxy):
    """
    Name server start() should raise an error if address is already in use.
    """
    with pytest.raises(RuntimeError) as error:
        run_nameserver(nsproxy.addr())
    assert 'OSError' in str(error.value)
    assert 'Address already in use' in str(error.value)


@skip_windows_any_port
def test_nameserver_permissionerror():
    """
    Name server start() should raise an error if it has not sufficient
    permissions.
    """
    with pytest.raises(RuntimeError) as error:
        run_nameserver('127.0.0.1:22')
    assert 'PermissionError' in str(error.value)
    assert 'Permission denied' in str(error.value)


def test_run_nameserver_base():
    """
    The `run_nameserver` function should accept a `base` parameter to specify
    the base NameServer class.
    """

    class BobMarley(NameServer):
        def get_up(self):
            return 'stand up!'

    ns = run_nameserver(base=BobMarley)
    assert ns.get_up() == 'stand up!'
    ns.shutdown()


def test_nameserver_spawn_process(nsproxy):
    """
    A name server should be able to spawn child processes.

    It is a way to make sure name servers are run as non-daemonic processes,
    which are not allowed to have children.
    """

    class Spawner(NameServer):
        def spawn_process(self):
            p = multiprocessing.Process()
            p.start()
            return True

    ns = run_nameserver(base=Spawner)
    assert ns.spawn_process()
    ns.shutdown()
