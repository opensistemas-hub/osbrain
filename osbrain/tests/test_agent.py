"""
Test file for agents.
"""
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
from osbrain import Proxy
from osbrain.helper import agent_dies
from osbrain.helper import logger_received
from osbrain.helper import sync_agent_logger
from osbrain.helper import wait_agent_attr

from common import nsproxy  # pragma: no flakes


def set_received(agent, message, topic=None):
    agent.received = message


def receive(agent, message):
    agent.received.append(message)


def test_agent_uuid():
    """
    All agent identifiers should be unique strings.
    """
    N = 1000
    bunch = set(Agent().uuid for i in range(N))
    assert len(bunch) == N
    assert all(isinstance(identifier, str) for identifier in bunch)


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
    a0 = Proxy('a0', timeout=3.)
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

    address = puller.bind('PULL', alias='pull', handler=receive,
                          transport='tcp')

    pusher.connect(address, alias='push')
    puller.shutdown()
    assert agent_dies(puller, nsproxy)

    pusher.send('push', 'foo')
    pusher.close_sockets()
    # After this timeout, depending on linger value, 'foo' will no longer be
    # on queue to be sent
    time.sleep(sleep_time)

    puller = run_agent('puller', base=AgentTest)
    puller.bind('PULL', alias='pull', handler=receive, addr=address.address,
                transport='tcp')

    assert should_receive == wait_agent_attr(puller, data='foo', timeout=.2)


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
    while not a1.get_attr('received'):
        time.sleep(0.01)
    assert a1.get_attr('received') == message


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
    Setting an agent's logger should result in the agnet actually sending
    log messages to the logger.
    """
    logger = run_logger('logger')
    a0 = run_agent('a0')
    a0.set_logger(logger)
    message = 'Hello world'
    while True:
        a0.log_info(message)
        history = logger.get_attr('log_history')
        if len(history):
            break
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
    while not server.get_attr('received').get('pull'):
        time.sleep(0.01)
    assert server.get_attr('received')['pull'] == 'Hello world!'


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
    while not receiver.get_attr('third'):
        time.sleep(0.01)
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
    assert logger_received(logger, 'log_history_info', message)
    # Log warning
    message = str(uuid4())
    agent.log_warning(message)
    assert logger_received(logger, 'log_history_warning', message)
    # Log error
    message = str(uuid4())
    agent.log_error(message)
    assert logger_received(logger, 'log_history_error', message)
    # Log debug
    message = str(uuid4())
    agent.set_attr(_DEBUG=True)
    agent.log_debug(message)
    assert logger_received(logger, 'log_history_debug', message)
    message = str(uuid4())
    agent.set_attr(_DEBUG=False)
    agent.log_debug(message)
    assert not logger_received(logger, 'log_history_debug', message)
    message = str(uuid4())
    agent.set_attr(_DEBUG=True)
    agent.log_debug(message)
    assert logger_received(logger, 'log_history_debug', message)


def test_running_exception(nsproxy):
    """
    An exception that occurs while the agent is running should stop the
    agent and log an error message as well.
    """
    logger = run_logger('logger')
    agent = run_agent('crasher')
    agent.set_logger(logger)
    assert agent.get_attr('running')
    # Make sure agent and logger are connected
    sync_agent_logger(agent, logger)
    # Raise an exception
    with pytest.raises(RuntimeError):
        agent.raise_exception()
    message = 'User raised an exception'
    assert logger_received(logger, 'log_history_error', message)
    assert not agent.get_attr('running')


def test_agent_error_address_already_in_use(nsproxy):
    """
    Running an agent should raise an error if address is already in use.
    """
    with pytest.raises(RuntimeError) as error:
        run_agent('a0', nsaddr=nsproxy.addr(), addr=nsproxy.addr())
    assert 'OSError' in str(error.value)
    assert 'Address already in use' in str(error.value)


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
    assert agent.get_attr('running')
    agent.stop()
    assert not agent.get_attr('keep_alive')
    while agent.get_attr('running'):
        time.sleep(0.01)
    assert not agent.get_attr('running')
