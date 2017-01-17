"""
Test file for agents.
"""
import os
import time
import random
from uuid import uuid4
from threading import Timer

import pytest

from osbrain import run_logger
from osbrain import run_agent
from osbrain import Agent
from osbrain import AgentProcess
from osbrain import Proxy
from osbrain import NSProxy
from osbrain import SocketAddress

from common import nsaddr  # pragma: no flakes
from common import nsproxy  # pragma: no flakes


def set_received(agent, message, topic=None):
    agent.received = message


def sync_agent_logger(agent, logger):
    while not len(logger.get_attr('log_history_info')):
        message = str(uuid4())
        agent.log_info(message)
        time.sleep(0.01)
    while message not in logger.get_attr('log_history_info')[-1]:
        time.sleep(0.01)


def logger_received(logger, log, message, timeout=1.):
    t0 = time.time()
    while message not in logger.get_attr(log)[-1]:
        time.sleep(0.01)
        if timeout and time.time() - t0 > timeout:
            return False
    return True


def test_early_agent_proxy(nsaddr):
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
    assert a0.ready() == 'OK'


def test_agent_loopback(nsaddr):
    """
    An agent should always have a _loopback_safe inproc socket.
    """
    a0 = run_agent('a0')
    assert a0.addr('_loopback_safe') == 'inproc://_loopback_safe'


def test_ping(nsaddr):
    """
    Test simple agent ping.
    """
    a0 = run_agent('a0')
    assert a0.ping() == 'pong'


def test_agent_shutdown(nsaddr):
    """
    An agent must unregister itself before shutting down.
    """
    agent = AgentProcess('a0', nsaddr)
    agent.start()
    a0 = Proxy('a0', nsaddr)
    a0.run()
    ns = NSProxy(nsaddr)
    assert 'a0' in ns.list()
    a0.shutdown()
    agent.join()
    assert 'a0' not in ns.list()


def test_set_method(nsaddr):
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


def test_set_method_lambda(nsaddr):
    """
    Set new methods for the agent using lambda functions.
    """
    a0 = run_agent('a0')
    a0.set_method(square=lambda agent, x: x ** 2)
    assert a0.square(2) == 4


def test_set_and_get_attributes(nsaddr):
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


def test_socket_creation(nsaddr):
    """
    Test ZMQ socket creation.
    """
    a0 = run_agent('a0')
    a0.bind('REQ', 'alias0')
    a0.bind('PUB', 'alias1')
    a0.bind('PUSH', 'alias2')
    addresses = a0.get_attr('address')
    assert 'alias0' in addresses
    assert 'alias1' in addresses
    assert 'alias2' in addresses


def test_reqrep(nsaddr):
    """
    Simple request-reply pattern between two agents.
    """
    def rep_handler(agent, message):
        return 'OK'

    a0 = run_agent('a0')
    a1 = run_agent('a1')
    addr = a0.bind('REP', 'reply', rep_handler)
    a1.connect(addr, 'request')
    response = a1.send_recv('request', 'Hello world')
    assert response == 'OK'


def test_reqrep_lambda(nsaddr):
    """
    Simple request-reply pattern between two agents using lambda handler.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    addr = a0.bind('REP', 'reply', lambda agent, message: 'x' + message)
    a1.connect(addr, 'request')
    response = a1.send_recv('request', 'Hello world')
    assert response == 'xHello world'


def test_pushpull(nsaddr):
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


def test_pubsub(nsaddr):
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


def test_agent_inheritance(nsaddr):
    """
    Test agent inheritance; agents can be based on a custom class.
    """
    class NewAgent(Agent):
        def the_answer_to_life(self):
            return 42

    # Test an Agent based on the new class
    AgentProcess('new', nsaddr=nsaddr, base=NewAgent).start()
    new = Proxy('new', nsaddr)
    new.run()
    assert new.the_answer_to_life() == 42

    # Test the quick `run_agent` function
    a0 = run_agent('a0', nsaddr, base=NewAgent)
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


def test_set_logger(nsaddr):
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


def test_agent_connect_repeat(nsaddr):
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


def test_agent_connect_repeat_new_handler(nsaddr):
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


def test_method_handlers(nsaddr):
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


def test_list_of_handlers(nsaddr):
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


# TODO:
#  - Test handler with 2 parameters (agent, message)
#  - Test handler with 3 parameters (agent, message, topic)
#  - Test topic is properly filtered (no match, partial match, full match)


def test_log_levels(nsaddr):
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


def test_running_exception(nsaddr):
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


def test_agent_error_address_already_in_use(nsaddr):
    """
    Running an agent should raise an error if address is already in use.
    """
    with pytest.raises(RuntimeError) as error:
        run_agent('a0', nsaddr=nsaddr, addr=nsaddr)
    assert 'OSError' in str(error.value)
    assert 'Address already in use' in str(error.value)


def test_agent_error_permission_denied(nsaddr):
    """
    Running an agent should raise an error if it has not sufficient
    permissions for binding to the address.
    """
    with pytest.raises(RuntimeError) as error:
        run_agent('a0', nsaddr=nsaddr, addr='127.0.0.1:22')
    assert 'PermissionError' in str(error.value)
    assert 'Permission denied' in str(error.value)


def test_agent_loopback_header_unknown(nsaddr):
    """
    Test an unknown header on loopback handler.
    """
    logger = run_logger('logger')
    agent = run_agent('a0')
    agent.set_logger(logger)
    # Make sure agent and logger are connected
    while not len(logger.get_attr('log_history_info')):
        agent.log_info('foo')
        time.sleep(0.01)
    agent.set_method(
        loopback_unknown=lambda a: a._handle_loopback(('UNKNOWN_HEADER', 1)))
    response = agent.loopback_unknown()
    history = []
    while not history:
        history = logger.get_attr('log_history_error')
    assert 'Unrecognized loopback message' in history[-1]
    assert 'Unrecognized loopback message' in response


def test_agent_stop(nsaddr):
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


def test_agent_bind_transport(nsaddr):
    """
    Test agent binding using TCP and IPC transport layers.
    """
    agent = run_agent('a0')
    # Default transport
    address = agent.bind('PUSH')
    assert address.transport == 'ipc'
    # Force IPC and TCP
    address = agent.bind('PUSH', transport='ipc')
    assert address.transport == 'ipc'
    address = agent.bind('PUSH', transport='tcp')
    assert address.transport == 'tcp'
    # Set IPC and TCP through environment variable
    os.environ['OSBRAIN_DEFAULT_TRANSPORT'] = 'tcp'
    address = agent.bind('PUSH', transport='tcp')
    assert address.transport == 'tcp'
    os.environ['OSBRAIN_DEFAULT_TRANSPORT'] = 'ipc'
    address = agent.bind('PUSH', transport='ipc')
    assert address.transport == 'ipc'


def test_agent_bind_given_address(nsaddr):
    """
    Test agent binding to an specified address using TCP and IPC transport
    layers.
    """
    agent = run_agent('a0')
    # IPC
    ipc_addr = str(uuid4())
    address = agent.bind('PUSH', addr=ipc_addr, transport='ipc')
    assert address.transport == 'ipc'
    assert address.address == ipc_addr
    # TCP
    while True:
        try:
            # Bind to random port
            port = random.randrange(10000, 20000)
            tcp_addr = '127.0.0.1:%s' % port
            tcp_addr = SocketAddress('127.0.0.1', port)
            address = agent.bind('PUSH', addr=tcp_addr, transport='tcp')
            break
        except Exception:
            pass
    assert address.transport == 'tcp'
    assert address.address == tcp_addr
