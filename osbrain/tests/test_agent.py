"""
Test file for agents.
"""
import time
from threading import Timer
from osbrain.logging import run_logger
from osbrain.core import run_agent
from osbrain.core import Agent
from osbrain.core import AgentProcess
from osbrain.proxy import Proxy
from osbrain.proxy import NSProxy

from common import nsaddr  # pragma: no flakes
from common import nsproxy  # pragma: no flakes


def set_received(agent, message, topic=None):
    agent.received = message


def test_early_agent_proxy(nsaddr):
    """
    It must be possible to create a Proxy when the registration of the new
    agent is imminent, even if it has not occured yet. A timeout will occur
    in case the agent could not be located.
    """
    agent = AgentProcess('a0', nsaddr)
    # Start agent later
    Timer(1, agent.start).start()
    # Locate agent now
    a0 = Proxy('a0', nsaddr)
    assert a0.test() == 'OK'


def test_agent_loopback(nsaddr):
    """
    An agent should always have a loopback inproc socket.
    """
    a0 = run_agent('a0')
    assert a0.addr('loopback') == 'inproc://loopback'


def test_ping(nsaddr):
    """
    Test simple loopback ping.
    """
    a0 = run_agent('a0')
    assert a0.ping() == 'PONG'


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


def test_logger(nsaddr):
    """
    Test basic logging.
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


def test_method_handlers(nsaddr):
    """
    Test handlers which are methods of a custom class.
    """
    class NewAgent(Agent):
        def on_init(self):
            self.received = {}
            self.bind('REP', 'rep', handler=self.rep)
            self.bind('PULL', 'pull', handler=self.pull)

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


# TODO:
#  - Test handler with 2 parameters (agent, message)
#  - Test handler with 3 parameters (agent, message, topic)
#  - Test topic is properly filtered (no match, partial match, full match)
