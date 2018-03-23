"""
Test file for agents.
"""
import os
import multiprocessing
import random
import time
from uuid import uuid4
from threading import Timer

import pytest
import Pyro4

import osbrain
from osbrain import run_logger
from osbrain import run_agent
from osbrain import Agent
from osbrain import AgentAddress
from osbrain import AgentProcess
from osbrain import SocketAddress
from osbrain import Proxy
from osbrain.helper import agent_dies
from osbrain.helper import logger_received
from osbrain.helper import sync_agent_logger
from osbrain.helper import wait_agent_attr

from common import nsproxy  # noqa: F401
from common import append_received
from common import set_received

from common import skip_windows_spawn
from common import skip_windows_any_port
from common import skip_windows_port_reuse


def test_agent_uuid():
    """
    All agent identifiers should be unique strings.
    """
    N = 100
    bunch = set(Agent()._uuid for i in range(N))
    assert len(bunch) == N
    assert all(isinstance(identifier, bytes) for identifier in bunch)


def test_agent_auto_generated_name(nsproxy):
    """
    If an agent is initialized without a name, a globally unique one must be
    auto generated for it.
    """
    count = 10
    names = set([run_agent().get_attr('name') for x in range(count)])
    assert all(isinstance(name, str) for name in names)
    assert len(names) == count
    assert names == set(nsproxy.agents())


def test_early_agent_proxy(nsproxy):
    """
    It must be possible to create a Proxy when the registration of the new
    agent is imminent, even if it has not occured yet. A timeout will occur
    in case the agent could not be located.
    """
    agent = AgentProcess('a0')
    # Start agent later
    Timer(2, agent.start).start()
    # Locate agent now
    with pytest.raises(Pyro4.errors.NamingError):
        a0 = Proxy('a0', timeout=1.)
    a0 = Proxy('a0', timeout=10.)
    # Just check agent is ready
    assert a0.unsafe.ping() == 'pong'


def test_agent_loopback(nsproxy):
    """
    An agent should always have a _loopback_safe inproc socket.
    """
    a0 = run_agent('a0')
    assert a0.addr('_loopback_safe') == \
        AgentAddress(transport='inproc', address='_loopback_safe',
                     kind='REP', role='server', serializer='pickle')


def test_ping(nsproxy):
    """
    Test simple agent ping.
    """
    a0 = run_agent('a0')
    assert a0.ping() == 'pong'


def test_late_runner(nsproxy):
    """
    The `run_agent` function should always make sure the agent is actually
    running before returning its proxy.
    """
    class LateRunner(Agent):
        @Pyro4.oneway
        def run(self):
            time.sleep(1)
            super().run()

    t0 = time.time()
    a0 = run_agent('a0', base=LateRunner)
    assert time.time() - t0 > 1
    assert a0.ping() == 'pong'


def test_agent_before_loop(nsproxy):
    """
    Tests agent's `before_loop()` method, which should be able to start timers.
    """
    class MyAgent(Agent):
        def on_init(self):
            self.x = 0

        def before_loop(self):
            self.each(.5, 'incr')

        def incr(self):
            self.x += 1

    agent = run_agent('agent', base=MyAgent)
    assert wait_agent_attr(agent, 'x', value=3, timeout=1.2)


def test_agent_shutdown(nsproxy):
    """
    An agent must unregister itself before shutting down.
    """
    agent = AgentProcess('a0', nsproxy.addr())
    agent.start()
    a0 = Proxy('a0', nsproxy.addr())
    a0.run()
    assert 'a0' in nsproxy.list()
    a0.shutdown()
    agent.join()
    assert 'a0' not in nsproxy.list()


def test_run_agent_initial_attributes(nsproxy):
    """
    The user can specify a set of attributes to be set in the agent when
    creating it.
    """
    a0 = run_agent('a0', attributes=dict(x=1, y='a'))
    assert a0.get_attr('x') == 1
    assert a0.get_attr('y') == 'a'


def test_run_agent_initial_attributes_exception(nsproxy):
    """
    The user can specify a set of attributes to be set in the agent when
    creating it. If the attribute specified overrites an existing attribute,
    an exception will be raised.
    """
    with pytest.raises(RuntimeError) as error:
        run_agent('a0', attributes=dict(name='foo'))
    assert 'KeyError' in str(error.value)
    assert 'Agent already has "name" attribute!' in str(error.value)


def test_set_method(nsproxy):
    """
    Set new methods for the agent.
    """
    def square(agent, x):
        return x ** 2

    def one(agent):
        return 1

    def two(agent):
        return 2

    a0 = run_agent('a0')
    # Single method, same name
    a0.set_method(square)
    assert a0.square(3) == 9
    # Multiple methods, same name
    a0.set_method(one, two)
    assert a0.one() == 1
    assert a0.two() == 2
    # Single method, change name
    a0.set_method(xx=square)
    assert a0.xx(3) == 9
    # Multiple methods, change name
    a0.set_method(uno=one, dos=two)
    assert a0.uno() == 1
    assert a0.dos() == 2


def test_set_method_lambda(nsproxy):
    """
    Set new methods for the agent using lambda functions.
    """
    a0 = run_agent('a0')
    a0.set_method(square=lambda agent, x: x ** 2)
    assert a0.square(2) == 4


def test_set_and_get_attributes(nsproxy):
    """
    Set and get attributes through the proxy.
    """
    def increment(agent):
        agent.zero += 10
        agent.one += 10
        agent.two += 10

    a0 = run_agent('a0')
    a0.set_method(increment)
    # Single attribute
    a0.zero = 0
    assert a0.zero == 0
    # Multiple attributes
    a0.set_attr(one=1, two=2)
    assert a0.one == 1
    assert a0.two == 2
    # Make sure the attributes come from the remote object
    a0.increment()
    assert a0.zero == 10
    assert a0.one == 11
    assert a0.two == 12


def test_socket_creation(nsproxy):
    """
    Test ZMQ socket creation.
    """
    a0 = run_agent('a0')
    addr0 = a0.bind('REQ', 'alias0')
    addr1 = a0.bind('PUB', 'alias1')
    addr2 = a0.bind('PUSH', 'alias2')
    assert a0.addr('alias0') == addr0
    assert a0.addr('alias1') == addr1
    assert a0.addr('alias2') == addr2


@pytest.mark.parametrize('host', ['127.0.0.1', '0.0.0.0'])
def test_bind_tcp_addr_random_port(nsproxy, host):
    """
    When using TCP transport, the bind method allows the user to specify the
    network interface to bind to. When no port is specified, a random one will
    be used.
    """
    agent = run_agent('a0')
    address = agent.bind('PUB', transport='tcp', addr=host)
    assert isinstance(address.address, SocketAddress)
    assert address.address.host == host
    assert address.address.port > 0


@pytest.mark.flaky(reruns=5)
def test_bind_tcp_addr_specific_port(nsproxy):
    """
    When using TCP transport, the bind method allows the user to specify the
    network interface and the port to bind to. If the port is specified, it
    must be used.
    """
    agent = run_agent('a0')
    host = '127.0.0.1'
    port = random.randrange(10000, 20000)
    addr = '{host}:{port}'.format(host=host, port=port)
    address = agent.bind('PUB', transport='tcp', addr=addr)
    assert isinstance(address.address, SocketAddress)
    assert address.address.host == host
    assert address.address.port == port


@skip_windows_spawn
@pytest.mark.parametrize('linger, sleep_time, should_receive', [
    (2, 1, True),
    (0.5, 1, False),
    (0, 1, False),
    (-1, 1, True),
])
def test_linger(nsproxy, linger, sleep_time, should_receive):
    '''
    Test linger works when closing the sockets of an agent.
    '''
    class AgentTest(Agent):
        def on_init(self):
            self.received = []

    osbrain.config['LINGER'] = linger

    puller = run_agent('puller', base=AgentTest)
    pusher = run_agent('pusher', base=AgentTest)

    address = puller.bind('PULL', alias='pull', handler=append_received,
                          transport='tcp')

    pusher.connect(address, alias='push')

    # Make sure connection is well established
    pusher.send('push', 'ping')
    assert wait_agent_attr(puller, data='ping', timeout=1)

    # Shutdown the puller and restart it without binding
    puller.shutdown()
    assert agent_dies('puller', nsproxy)
    puller = run_agent('puller', base=AgentTest)

    # Push a new message, which should block during linger period
    pusher.send('push', 'foo')
    pusher.close_all()

    # After this timeout, depending on linger value, 'foo' will no longer be
    # on queue to be sent
    time.sleep(sleep_time)

    # Bind to receive the message (if still in queue)
    puller.bind('PULL', alias='pull', handler=append_received,
                addr=address.address, transport='tcp')

    assert should_receive == wait_agent_attr(puller, data='foo', timeout=1)


def test_pushpull(nsproxy):
    """
    Simple push-pull pattern test.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    a1.set_attr(received=None)
    addr = a1.bind('PULL', handler=set_received)
    a0.connect(addr, 'push')
    message = 'Hello world'
    a0.send('push', message)
    assert wait_agent_attr(a1, name='received', value=message)


def test_pubsub(nsproxy):
    """
    Simple publisher-subscriber pattern test.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    a1.set_attr(received=None)
    addr = a0.bind('PUB', alias='pub')
    a1.connect(addr, handler=set_received)
    message = 'Hello world'
    while not a1.get_attr('received'):
        a0.send('pub', message)
        time.sleep(0.1)
    assert a1.get_attr('received') == message


def test_agent_inheritance(nsproxy):
    """
    Test agent inheritance; agents can be based on a custom class.
    """
    class NewAgent(Agent):
        def the_answer_to_life(self):
            return 42

    # Test an Agent based on the new class
    AgentProcess('new', nsaddr=nsproxy.addr(), base=NewAgent).start()
    new = Proxy('new', nsproxy.addr())
    new.run()
    assert new.the_answer_to_life() == 42

    # Test the quick `run_agent` function
    a0 = run_agent('a0', nsproxy.addr(), base=NewAgent)
    assert a0.the_answer_to_life() == 42


def test_agent_multiproxy(nsproxy):
    """
    Test agent multiproxy access; all proxies should access the same agent
    object.
    """
    class NewAgent(Agent):
        def on_init(self):
            self.count = 0

        def add(self):
            self.count += 1

        def total(self):
            return self.count

    agent = run_agent('Counter', base=NewAgent)
    agent.add()
    assert agent.total() == 1

    newproxy = nsproxy.proxy('Counter')
    newproxy.add()
    assert agent.total() == 2


def test_set_logger(nsproxy):
    """
    Setting an agent's logger should result in the agent actually sending
    log messages to the logger.
    """
    logger = run_logger('logger')
    a0 = run_agent('a0')
    a0.set_logger(logger)

    message = 'Hello world'
    a0.each(0.1, 'log_info', message)

    assert wait_agent_attr(logger, name='log_history', length=1)

    history = logger.get_attr('log_history')
    assert message in history[0]


def test_set_logger_wrong(nsproxy):
    """
    Setting an agent's logger incorrectly should result in an exception
    being raised.
    """
    a0 = run_agent('a0')
    with pytest.raises(ValueError):
        a0.set_logger(1.4142)


def test_agent_connect_repeat(nsproxy):
    """
    Test connecting from an agent to the same address that the agent
    connected to just before. When no new handler is given, the agent simply
    adds a new alias. Both aliases should work as expected.
    """
    def rep_handler(agent, message):
        return 'OK'

    server = run_agent('a0')
    client = run_agent('a1')
    addr = server.bind('REP', 'reply', rep_handler)
    client.connect(addr, alias='request0')
    client.connect(addr, alias='request1')
    assert client.send_recv('request0', 'Hello world') == 'OK'
    assert client.send_recv('request1', 'Hello world') == 'OK'


def test_agent_connect_repeat_new_handler(nsproxy):
    """
    Test connecting from an agent to the same address that the agent
    connected to just before. When a new handler is given, the result is
    an exception (not implemented).
    """
    sender = run_agent('a0')
    receiver = run_agent('a1')
    addr = sender.bind('PUSH', alias='push')
    receiver.connect(addr, alias='pull0', handler=set_received)
    with pytest.raises(NotImplementedError):
        receiver.connect(addr, alias='pull1', handler=set_received)


def test_method_handlers(nsproxy):
    """
    Test handlers which are methods of a custom class.
    """
    class NewAgent(Agent):
        def on_init(self):
            self.received = {}
            # Set a handler with a method type
            self.bind('REP', 'rep', handler=self.rep)
            # Set a handler with a string type
            self.bind('PULL', 'pull', handler='pull')

        def rep(self, message):
            self.received['rep'] = message
            return 'OK'

        def pull(self, message):
            self.received['pull'] = message

    server = run_agent('server', base=NewAgent)
    client = run_agent('client')
    # Request
    client.connect(server.addr('rep'), 'req')
    assert client.send_recv('req', 'This is a request') == 'OK'
    assert server.get_attr('received')['rep'] == 'This is a request'
    # Push
    client.connect(server.addr('pull'), 'push')
    client.send('push', 'Hello world!')
    received = {'rep': 'This is a request', 'pull': 'Hello world!'}
    assert wait_agent_attr(server, name='received', value=received)


def test_list_of_handlers(nsproxy):
    """
    An agent should accept a list of handlers. These handlers should be
    executed in strict order.
    """
    class NewAgent(Agent):
        def on_init(self):
            self.received = None
            self.second = None
            self.third = None
            # Set handlers using a function, a method type and a string type
            self.bind('PULL', 'pull', handler=[set_received, self.pull0,
                                               'pull1'])

        def pull0(self, message):
            self.second = '0' + str(self.received)

        def pull1(self, message):
            self.third = '1' + str(self.second)

    sender = run_agent('sender')
    receiver = run_agent('receiver', base=NewAgent)
    sender.connect(receiver.addr('pull'), 'push')
    message = 'Hello world'
    sender.send('push', message)
    assert wait_agent_attr(receiver, name='third', value='10' + message)
    assert receiver.get_attr('received') == message
    assert receiver.get_attr('second') == '0' + message
    assert receiver.get_attr('third') == '10' + message


def test_invalid_handlers(nsproxy):
    """
    Invalid handlers should raise a TypeError.
    """
    agent = run_agent('test')
    with pytest.raises(TypeError):
        agent.bind('REP', handler=1.234)


def test_has_socket(nsproxy):
    """
    Test the has_socket method.
    """
    a0 = run_agent('a0')
    assert a0.has_socket('_loopback_safe')
    assert not a0.has_socket('pub')
    a0.bind('PUB', alias='pub')
    assert a0.has_socket('pub')


def test_close(nsproxy):
    """
    Test that closing a socket removes it from the socket entry.
    """
    a0 = run_agent('a0')
    a0.bind('PUB', alias='pub')

    a0.close('pub')
    assert not a0.has_socket('pub')


def test_close_all(nsproxy):
    """
    Test that after a call to `close_all`, only those non-internal are
    actually closed.
    """
    a0 = run_agent('a0')
    a0.bind('PUB', alias='pub')

    a0.close_all()
    assert not a0.has_socket('pub')
    assert a0.has_socket('_loopback_safe')


def test_log_levels(nsproxy):
    """
    Test different log levels: info, warning, error and debug. Debug messages
    are only to be logged if `_DEBUG` attribute is set in the agent.
    """
    logger = run_logger('logger')
    agent = run_agent('a0')
    agent.set_logger(logger)
    sync_agent_logger(agent, logger)
    # Log info
    message = str(uuid4())
    agent.log_info(message)
    assert logger_received(logger, message, log_name='log_history_info')
    # Log warning
    message = str(uuid4())
    agent.log_warning(message)
    assert logger_received(logger, message, log_name='log_history_warning')
    # Log error
    message = str(uuid4())
    agent.log_error(message)
    assert logger_received(logger, message, log_name='log_history_error')
    # Log debug
    message = str(uuid4())
    agent.set_attr(_DEBUG=True)
    agent.log_debug(message)
    assert logger_received(logger, message, log_name='log_history_debug')
    message = str(uuid4())
    agent.set_attr(_DEBUG=False)
    agent.log_debug(message)
    assert not logger_received(logger, message, log_name='log_history_debug')
    message = str(uuid4())
    agent.set_attr(_DEBUG=True)
    agent.log_debug(message)
    assert logger_received(logger, message, log_name='log_history_debug')


def test_running_exception(nsproxy):
    """
    An exception that occurs while the agent is running should stop the
    agent and log an error message as well.
    """
    logger = run_logger('logger')
    agent = run_agent('crasher')
    agent.set_logger(logger)
    assert agent.is_running()
    # Make sure agent and logger are connected
    sync_agent_logger(agent, logger)
    # Raise an exception
    with pytest.raises(RuntimeError):
        agent.raise_exception()
    message = 'User raised an exception'
    assert logger_received(logger, message, log_name='log_history_error')
    assert not agent.is_running()


@skip_windows_port_reuse
def test_agent_error_address_already_in_use(nsproxy):
    """
    Running an agent should raise an error if address is already in use.
    """
    with pytest.raises(RuntimeError) as error:
        run_agent('a0', nsaddr=nsproxy.addr(), addr=nsproxy.addr())
    assert 'OSError' in str(error.value)
    assert 'Address already in use' in str(error.value)


@skip_windows_any_port
def test_agent_error_permission_denied(nsproxy):
    """
    Running an agent should raise an error if it has not sufficient
    permissions for binding to the address.
    """
    with pytest.raises(RuntimeError) as error:
        run_agent('a0', nsaddr=nsproxy.addr(), addr='127.0.0.1:22')
    assert 'PermissionError' in str(error.value)
    assert 'Permission denied' in str(error.value)


def test_agent_loopback_header_unknown(nsproxy):
    """
    Test an unknown header on loopback handler.
    """
    class Unknown(Agent):
        def unknown(self):
            self._loopback('UNKNOWN_HEADER', 1)

    logger = run_logger('logger')
    agent = run_agent('a0', base=Unknown)
    agent.set_logger(logger)
    # Make sure agent and logger are connected
    sync_agent_logger(agent, logger)
    agent.unsafe.unknown()
    history = []
    while not history:
        history = logger.get_attr('log_history_error')
    assert 'Unrecognized loopback message' in history[-1]


def test_agent_stop(nsproxy):
    """
    An agent will stop running when the `stop()` method is executed.
    """
    agent = run_agent('a0')
    assert agent.is_running()
    agent.stop()
    assert not agent.get_attr('_keep_alive')
    assert wait_agent_attr(agent, name='_running', value=False)


def test_agent_spawn_process(nsproxy):
    """
    An agent should be able to spawn child processes.

    It is a way to make sure agents are run as non-daemonic processes, which
    are not allowed to have children.
    """
    class Spawner(Agent):
        def spawn_process(self):
            p = multiprocessing.Process()
            p.start()
            return True

    agent = run_agent('a0', base=Spawner)
    assert agent.spawn_process()


def test_agent_execute_as_function(nsproxy):
    """
    Test `execute_as_function` method, which should execute a given function
    in the remote agent.
    """
    class EnvironmentAgent(Agent):
        def set_environment(self, value):
            os.environ['__OSBRAIN_TEST'] = value

    def name(prefix, suffix='suffix'):
        return prefix + os.environ.get('__OSBRAIN_TEST', '') + suffix

    agent0 = run_agent('a0', base=EnvironmentAgent)
    agent1 = run_agent('a1', base=EnvironmentAgent)
    agent0.set_environment('0')
    agent1.set_environment('1')

    assert agent0.execute_as_function(name, 'p') == 'p0suffix'
    assert agent0.execute_as_function(name, 'p', suffix='s') == 'p0s'
    assert agent1.execute_as_function(name, 'p') == 'p1suffix'
    assert agent1.execute_as_function(name, 'p', suffix='s') == 'p1s'


def test_agent_execute_as_method(nsproxy):
    """
    Test `execute_as_method` method, which should execute a given function
    in the remote agent as a method (i.e.: passing the agent as first
    parameter of the function).
    """
    def name(agent, prefix, suffix='suffix'):
        return prefix + agent.name + suffix

    agent0 = run_agent('a0')
    agent1 = run_agent('a1')

    assert agent0.execute_as_method(name, 'p') == 'pa0suffix'
    assert agent0.execute_as_method(name, 'p', suffix='s') == 'pa0s'
    assert agent1.execute_as_method(name, 'p') == 'pa1suffix'
    assert agent1.execute_as_method(name, 'p', suffix='s') == 'pa1s'


def test_agent_not_running_safe_call(nsproxy):
    """
    Trying to execute a `safe_call()` on an agent that is not running should
    raise an exception.
    """
    agent = run_agent('a0')
    assert agent.safe_call('ping') == 'pong'

    with pytest.raises(Exception):
        agent.raise_exception()
    assert wait_agent_attr(agent, name='_running', value=False)

    with pytest.raises(RuntimeError) as error:
        agent.safe_call('ping')
    assert 'Agent must be running' in str(error.value)
