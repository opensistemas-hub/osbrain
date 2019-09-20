"""
Proxy module tests.
"""
import pickle
import time
from threading import Timer

import pytest
from Pyro4.errors import ConnectionClosedError

import osbrain
from osbrain import Agent
from osbrain import AgentProcess
from osbrain import NameServer
from osbrain import Proxy
from osbrain import run_agent
from osbrain import run_nameserver
from osbrain.helper import wait_agent_attr
from osbrain.proxy import locate_ns

from .common import append_received


def since(t0, passed, tolerance):
    return abs((time.time() - t0) - passed) < tolerance


class BusyWorker(Agent):
    def on_init(self):
        self.bind('PULL', alias='pull', handler=self.stay_busy)
        self.busy = False

    def stay_busy(self, delay):
        self.busy = True
        time.sleep(delay)
        self.busy = False

    def listen(self):
        return 'OK'


def setup_busy_worker(nsproxy):
    worker = run_agent('worker', base=BusyWorker)
    boss = run_agent('boss')
    boss.connect(worker.addr('pull'), alias='push')
    # Make worker busy for 2 seconds
    boss.send('push', 2)
    assert wait_agent_attr(worker, name='busy', value=True, timeout=0.5)
    return worker


@pytest.mark.parametrize('timeout', [0, 1])
def test_wrong_nameserver_address(timeout):
    """
    Locating a name server that does not exist should raise an error after
    the defined timeout.
    """
    t0 = time.time()
    with pytest.raises(TimeoutError):
        locate_ns('127.0.0.1:1234', timeout=timeout)
    assert timeout <= time.time() - t0 <= timeout + 1.2


def test_no_timeout_locate_ns_existing(nsproxy):
    """
    Locating a NS that exists with no timeout should be OK.
    """
    locate_ns(nsproxy.addr(), timeout=0.0)


def test_proxy_without_nsaddr(nsproxy):
    """
    Creating a proxy without specifying the name server address should
    result in the OSBRAIN_NAMESERVER_ADDRESS being used.
    """
    agent0 = run_agent('foo')
    agent0.set_attr(x=1.0)
    agent1 = Proxy('foo')
    assert agent1.get_attr('x') == 1.0


def test_proxy_pickle_serialization(nsproxy):
    """
    Make sure proxies can be (de)serialized using pickle.
    """
    agent0 = run_agent('foo')
    agent0.set_attr(x=1.0)
    proxy = Proxy('foo')
    serialized = pickle.dumps(proxy)
    assert serialized
    deserialized = pickle.loads(serialized)
    assert deserialized
    assert deserialized.get_attr('x') == 1.0


def test_agent_proxy_remote_exceptions(nsproxy):
    """
    Remote exceptions on method executions should be raised locally by the
    proxy with information on what did go wrong remotely.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    with pytest.raises(TypeError) as error:
        a0.addr('asdf', 'qwer', 'foo', 'bar')
    assert 'positional arguments but 5 were given' in str(error.value)
    with pytest.raises(RuntimeError) as error:
        a1.raise_exception()
    assert 'User raised an exception' in str(error.value)


def test_agent_proxy_initialization_timeout(nsproxy):
    """
    An agent proxy should raise a TimeoutError at initialization if the agent
    is not ready after a number of seconds.
    """

    class InitTimeoutProxy(Proxy):
        def ping(self):
            time.sleep(0.1)
            raise TimeoutError()

    run_agent('foo')
    with pytest.raises(TimeoutError):
        InitTimeoutProxy('foo', timeout=1.0)


@pytest.mark.parametrize('timeout', [-1, 1])
def test_agent_proxy_wait_running(nsproxy, timeout):
    """
    Using `wait_for_running` on a proxy after initialization should block until
    the agent is running or time out.
    """
    AgentProcess('agent').start()

    # Get "offline" proxy
    agent = Proxy('agent')
    time0 = time.time()
    Timer(abs(timeout) / 2, agent.run).start()

    proxy = Proxy('agent').wait_for_running(timeout=timeout)
    elapsed = time.time() - time0
    assert proxy.ping() == 'pong'
    assert elapsed >= abs(timeout) / 2
    assert elapsed <= abs(timeout)


def test_agent_proxy_wait_running_0_seconds(nsproxy):
    """
    Using `wait_for_running` on a proxy after initialization should block until
    the agent is running or time out.
    """
    run_agent('agent')

    proxy = Proxy('agent').wait_for_running(timeout=0)
    assert proxy.ping() == 'pong'


@pytest.mark.parametrize('timeout', [0, 1])
def test_agent_proxy_wait_running_timeout(nsproxy, timeout):
    """
    Check that the `wait_for_running` method times out if the agent is not
    running after the specified number of seconds.
    """
    AgentProcess('agent').start()

    time0 = time.time()
    with pytest.raises(TimeoutError) as error:
        Proxy('agent').wait_for_running(timeout=timeout)
    elapsed = time.time() - time0

    assert 'Timed out' in str(error.value)
    assert elapsed >= timeout
    assert elapsed < timeout + 0.5


def test_agent_proxy_nameserver_address(nsproxy):
    """
    Agent proxies should be able to return the name server address.
    """
    agent = run_agent('foo')
    assert agent.nsaddr() == nsproxy.addr()


def test_agent_proxy_safe_and_unsafe_property(monkeypatch, nsproxy):
    """
    Using the safe/unsafe property from a proxy should allow us to
    override the environment global configuration.
    """
    run_agent('foo')
    # Safe environment
    monkeypatch.setitem(osbrain.config, 'SAFE', True)
    proxy = Proxy('foo')
    assert proxy._safe
    assert proxy.safe._safe
    assert not proxy.unsafe._safe
    # Unsafe environment
    monkeypatch.setitem(osbrain.config, 'SAFE', False)
    proxy = Proxy('foo')
    assert not proxy._safe
    assert proxy.safe._safe
    assert not proxy.unsafe._safe


def test_agent_run_agent_safe_and_unsafe(nsproxy):
    """
    Using the `run_agent` function should allow us to set a `safe` attribute
    for the returned Proxy as well.
    """
    safe = run_agent('a0', safe=True)
    unsafe = run_agent('a1', safe=False)
    assert safe._safe
    assert not unsafe._safe


def test_agent_proxy_safe_and_unsafe_parameter(monkeypatch, nsproxy):
    """
    Using the safe/unsafe parameter when initializing a proxy should allow
    us to override the environment global configuration.
    """
    run_agent('foo')
    # Safe environment
    monkeypatch.setitem(osbrain.config, 'SAFE', True)
    proxy = Proxy('foo')
    assert proxy._safe
    proxy = Proxy('foo', safe=False)
    assert not proxy._safe
    # Unsafe environment
    monkeypatch.setitem(osbrain.config, 'SAFE', False)
    proxy = Proxy('foo')
    assert not proxy._safe
    proxy = Proxy('foo', safe=True)
    assert proxy._safe


def test_agent_proxy_safe_and_unsafe_calls_property_safe(monkeypatch, nsproxy):
    """
    An agent can be accessed through a proxy in both safe and unsafe ways.
    When using the `safe` property, calls are expected to wait until the main
    thread is able to process them to avoid concurrency.
    """
    monkeypatch.setitem(osbrain.config, 'SAFE', False)
    worker = setup_busy_worker(nsproxy)
    assert not worker._safe
    t0 = time.time()
    assert worker.safe.listen() == 'OK'
    assert since(t0, passed=2.0, tolerance=0.1)
    assert not worker.get_attr('busy')
    # Calling a method with `.safe` should not change default behavior
    assert not worker._safe


def test_agent_proxy_safe_and_unsafe_calls_property_unsafe(
    monkeypatch, nsproxy
):
    """
    An agent can be accessed through a proxy in both safe and unsafe ways.
    When using the `unsafe` property, calls are not expected to wait until
    the main thread is able to process them (concurrency is allowed).
    """
    monkeypatch.setitem(osbrain.config, 'SAFE', True)
    worker = setup_busy_worker(nsproxy)
    assert worker._safe
    t0 = time.time()
    assert worker.unsafe.listen() == 'OK'
    assert since(t0, passed=0.0, tolerance=0.1)
    while worker.get_attr('busy'):
        time.sleep(0.01)
    assert since(t0, passed=2.0, tolerance=0.1)
    # Calling a method with `.unsafe` should not change default behavior
    assert worker._safe


def test_agent_proxy_safe_and_unsafe_calls_environ_safe(monkeypatch, nsproxy):
    """
    An agent can be accessed through a proxy in both safe and unsafe ways.
    When using the `safe` property, calls are expected to wait until the main
    thread is able to process them to avoid concurrency.
    """
    monkeypatch.setitem(osbrain.config, 'SAFE', True)
    worker = setup_busy_worker(nsproxy)
    t0 = time.time()
    assert worker.listen() == 'OK'
    assert since(t0, passed=2.0, tolerance=0.1)
    assert not worker.get_attr('busy')


def test_agent_proxy_safe_and_unsafe_calls_environ_unsafe(
    monkeypatch, nsproxy
):
    """
    An agent can be accessed through a proxy in both safe and unsafe ways.
    When using the `unsafe` property, calls are not expected to wait until
    the main thread is able to process them (concurrency is allowed).
    """
    monkeypatch.setitem(osbrain.config, 'SAFE', False)
    worker = setup_busy_worker(nsproxy)
    t0 = time.time()
    assert worker.listen() == 'OK'
    assert since(t0, passed=0.0, tolerance=0.1)
    while worker.get_attr('busy'):
        time.sleep(0.01)
    assert since(t0, passed=2.0, tolerance=0.1)


def test_agent_proxy_oneway(nsproxy):
    """
    User can force a one-way from the proxy.
    """

    class OneWayne(Agent):
        def on_init(self):
            target = self.bind(
                'PULL',
                alias='target',
                handler=append_received,
                transport='inproc',
            )
            self.target = target
            self.received = []

        def shoot(self):
            self.connect(self.target, alias='gun')
            for _ in range(10):
                self.send('gun', 'bang!')
                time.sleep(0.1)

    wayne = run_agent('wayne', base=OneWayne)

    # Execute one-way call, which should return soon
    assert not wayne._next_oneway
    t0 = time.time()
    assert not wayne.oneway.shoot()  # No return expected
    assert not wayne.oneway.shoot()  # No return expected
    assert time.time() - t0 < 0.2
    assert not wayne._next_oneway

    assert wait_agent_attr(wayne, value=20 * ['bang!'], timeout=1.5)


def test_nameserver_proxy_shutdown_connectionclosed():
    """
    Check that nameserver proxies can handle a ConnectionClosedError at
    shutdown.
    """

    class CustomNS(NameServer):
        def daemon_shutdown(self):
            super().daemon_shutdown()
            raise ConnectionClosedError

    ns = run_nameserver(base=CustomNS)
    ns.shutdown()
