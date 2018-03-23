"""
Test file for synchronized publications.
"""
import time

import pytest

from osbrain import Agent
from osbrain import run_agent
from osbrain import run_logger
from osbrain.helper import sync_agent_logger
from osbrain.helper import logger_received
from osbrain.helper import wait_agent_attr
from osbrain.helper import wait_agent_condition

from common import nsproxy  # noqa: F401
from common import append_received


class BaseServer(Agent):
    def publish(self):
        self.count += 1
        self.send('publish', self.count)

    def publish_str(self):
        self.count += 1
        self.send('publish', str(self.count), topic='positive')
        self.send('publish', str(-self.count), topic='negative')
        self.send('publish', 'bytes...', topic=b'\xeb')

    def reply(self, request):
        self.received.append((self.count, request))
        return self.count + 0.5


class Server(BaseServer):
    def on_init(self):
        self.count = 0
        self.received = []
        self.bind('SYNC_PUB', alias='publish', handler='reply')


class PubServer(BaseServer):
    def on_init(self):
        self.count = 0
        self.received = []
        self.bind('PUB', alias='publish', handler='reply')


class ServerYield(Server):
    def reply(self, request):
        yield self.count + 0.5
        self.received.append((self.count, request))


class ServerLate(Server):
    def reply(self, delay):
        self.received.append(delay)
        time.sleep(delay)
        return 'x' + str(delay)


class ServerNumbers(Agent):
    def publish(self):
        self.send('pub', 1, topic='negate')
        self.send('pub', 2, topic=b'normal')
        self.send('pub', 'not received', topic='topic_C')


class Client(Agent):
    def on_init(self):
        self.received = []
        self.error_log = []


def receive_negate(agent, response):
    agent.received.append(-response)


def on_error(agent):
    agent.error_log.append('error')


def match_tail(agent, data):
    return agent.received[-len(data):] == data


@pytest.mark.parametrize('socket_type', ['PUB', 'SYNC_PUB'])
def test_unsubscribe(nsproxy, socket_type):
    '''
    Test that unsubscribing from topics works fine.

    The server will be publishing the natural numbers, in ascending order,
    starting at one. Odd numbers will be sent with `odd` topic and even
    numbers with `even` topic.

    A subscriber will subscribe to all numbers, and then it will unsubscribe
    from the odd numbers.

    Two non consecutive numbers must be received consecutively at that point,
    since they both will be even.
    '''
    def check_non_consecutive(agent):
        """
        Check whether the last two received numbers are non-consecutive.
        """
        return agent.received[-1] - agent.received[-2] != 1

    def publish(agent):
        assert agent.count % 2 == 1
        agent.send('pub', agent.count, topic='odd')
        agent.send('pub', agent.count + 1, topic='even')
        agent.count += 2

    # Set up the agents
    server = run_agent('server')
    client = run_agent('client', base=Client)

    server.set_attr(count=1)
    addr = server.bind(socket_type, alias='pub', handler=append_received)
    client.connect(addr, alias='sub', handler={'odd': append_received,
                                               'even': append_received})

    # Make sure the connection is established
    server.each(0.1, 'send', 'pub', 'connecting...', topic='odd', alias='tmp')
    assert wait_agent_attr(client, data='connecting...')
    server.stop_timer('tmp')

    # Wait until client receives some numbers
    client.set_attr(received=[])
    server.each(0.1, publish)
    assert wait_agent_attr(client, length=5)
    assert not client.execute_as_method(check_non_consecutive)

    # Unsubscribe from odd numbers (receiving only even numbers)
    client.unsubscribe('sub', 'odd')

    assert wait_agent_condition(client, check_non_consecutive)
    assert client.get_attr('received')[-1] % 2 == 0


@pytest.mark.parametrize('socket_type', ['PUB', 'SYNC_PUB'])
def test_unsubscribe_various(nsproxy, socket_type):
    '''
    Test that unsubscribing from various topics works fine.

    The server will be publishing zeroes through two topics quickly, and
    ones through a single topic slowly.

    A subscriber will subscribe to all numbers, and then unsubscribe from the
    topics related to the zeroes, therefore receiving three (or more) ones in
    a row.
    '''
    def check_sum_three(agent):
        """
        Check whether the last three received numbers sum to three.

        For this test in particular, the last three numbers should be one,
        received through the 'one' topic.
        """
        return sum(agent.received[-3:]) == 3

    def publish_zeroes(agent):
        agent.send('pub', 0, topic='zero')
        agent.send('pub', 0, topic='other_zero')

    def publish_one(agent):
        agent.send('pub', 1, topic='one')

    # Set up the agents
    server = run_agent('server')
    client = run_agent('client', base=Client)

    addr = server.bind(socket_type, alias='pub', handler=append_received)
    client.connect(addr, alias='sub', handler={'zero': append_received,
                                               'other_zero': append_received,
                                               'one': append_received})

    # Make sure the connection is established
    server.each(0.1, 'send', 'pub', 'connecting...', topic='zero', alias='tmp')
    assert wait_agent_attr(client, data='connecting...')
    server.stop_timer('tmp')

    # Wait until client receives some numbers
    client.set_attr(received=[])
    server.each(0.1, publish_zeroes)
    server.each(0.2, publish_one)
    assert wait_agent_attr(client, length=5)
    assert not client.execute_as_method(check_sum_three)

    # Unsubscribe from zeroes numbers (receiving only ones)
    client.unsubscribe('sub', ('zero', 'other_zero'))

    assert wait_agent_condition(client, check_sum_three)


@pytest.mark.parametrize('socket_type', ['PUB', 'SYNC_PUB'])
@pytest.mark.parametrize('subscribe_separately', [True, False])
def test_subscribe(nsproxy, socket_type, subscribe_separately):
    '''
    Test subscribing to various topics/handlers works fine.
    '''
    server = run_agent('server', base=ServerNumbers)
    client = run_agent('client')

    addr = server.bind(socket_type, alias='pub', handler=append_received)
    client.set_attr(received=[])
    client.connect(addr, alias='sub', handler=append_received)

    # Establish a connection
    server.each(0.1, 'send', 'pub', 'connecting...', alias='tmp')
    assert wait_agent_attr(client, data='connecting...')
    server.stop_timer('tmp')

    # Subscribe to two topics. Client should only receive -1 and 2.
    client.unsubscribe('sub', '')
    if subscribe_separately:
        client.subscribe('sub', handler={'negate': receive_negate})
        client.subscribe('sub', handler={'normal': append_received})
    else:
        client.subscribe('sub', handler={'negate': receive_negate,
                                         'normal': append_received})

    server.each(0.1, 'publish')

    assert wait_agent_condition(client, match_tail, [-1, 2] * 4)


@pytest.mark.parametrize('socket_type', ['PUB', 'SYNC_PUB'])
def test_resubscribe(nsproxy, socket_type):
    '''
    After subscribing to the same topic with a different handler after a
    subscription to that topic was already made, we should override the
    original handler.

    Note that we will only override explicitly given topics (previous
    subscriptions of other topics will remain untouched).
    '''
    server = run_agent('server', base=ServerNumbers)
    client = run_agent('client')

    addr = server.bind(socket_type, alias='pub', handler=append_received)
    client.set_attr(received=[])
    client.connect(addr, alias='sub', handler=append_received)

    # Establish a connection
    server.each(0.1, 'send', 'pub', 'connecting...', alias='tmp')
    assert wait_agent_attr(client, data='connecting...')
    server.stop_timer('tmp')

    # Subscribe to two topics
    client.unsubscribe('sub', '')
    client.subscribe('sub', handler={'negate': receive_negate,
                                     'normal': append_received})

    server.each(0.1, 'publish')

    assert wait_agent_condition(client, match_tail, [-1, 2] * 4)

    # Resubscribe, so as to store the 'normal' (2) messages negated
    client.subscribe('sub', handler={'normal': receive_negate})

    assert wait_agent_condition(client, match_tail, [-1, -2] * 4)


@pytest.mark.parametrize('socket_type', ['PUB', 'SYNC_PUB'])
def test_unsubscribe_and_subscribe_again(nsproxy, socket_type):
    '''
    Test resubscribing to topics after unsubscribing works fine.
    '''
    server = run_agent('server', base=ServerNumbers)
    client = run_agent('client')

    addr = server.bind(socket_type, alias='pub', handler=append_received)
    client.set_attr(received=[])
    client.connect(addr, alias='sub', handler=append_received)

    # Establish a connection
    server.each(0.1, 'send', 'pub', 'connecting...', alias='tmp')
    assert wait_agent_attr(client, data='connecting...')
    server.stop_timer('tmp')

    # Subscribe to two topics
    client.unsubscribe('sub', '')
    client.subscribe('sub', handler={'negate': receive_negate,
                                     'normal': append_received})

    # Make server to start publishing messages
    server.each(0.1, 'publish')

    assert wait_agent_condition(client, match_tail, [-1, 2] * 4)

    # Unsubscribe from one topic
    client.unsubscribe('sub', 'negate')

    assert wait_agent_condition(client, match_tail, [2] * 8)

    # Subscribe again
    client.subscribe('sub', handler={'negate': receive_negate})

    assert wait_agent_condition(client, match_tail, [-1, 2] * 4)


@pytest.mark.parametrize('server', [Server, PubServer])
def test_simple_pub_single_handler(nsproxy, server):
    """
    SYNC_PUB should work just like a normal PUB. This test checks normal
    behavior when using a single handler (i.e.: no filtering).

    When clients connect to a SYNC_PUB server, as long as they do not make
    requests, this communication pattern should behave exactly like a normal
    PUB-SUB pattern.
    """
    server = run_agent('server', base=server)
    alltopics = run_agent('alltopics', base=Client)

    # Connect clients
    addr = server.addr('publish')
    addr_alltopics = alltopics.connect(addr, handler=append_received)
    assert addr_alltopics == addr.twin()

    # Publish from server
    server.each(0, 'publish_str')

    # Wait for clients to receive some data
    N = 10
    assert wait_agent_attr(alltopics, length=N)

    # alltopics
    received = [int(x) if x != 'bytes...' else x
                for x in alltopics.get_attr('received')]
    assert len(received) >= N
    for i in range(2, len(received)):
        if received[i] == 'bytes...':
            assert received[i - 1] == -received[i - 2]
        elif received[i] > 0:
            assert received[i - 1] == 'bytes...'
            assert received[i - 2] == -received[i] + 1
        else:
            assert received[i - 1] == -received[i]
            assert received[i - 2] == 'bytes...'


@pytest.mark.parametrize('server', [Server, PubServer])
def test_simple_pub_dict_handler(nsproxy, server):
    """
    SYNC_PUB should work just like a normal PUB. This test checks normal
    behavior when using multiple handlers (i.e.: filtering).

    When clients connect to a SYNC_PUB server, as long as they do not make
    requests, this communication pattern should behave exactly like a normal
    PUB-SUB pattern.
    """
    server = run_agent('server', base=server)
    both = run_agent('both', base=Client)
    positive = run_agent('positive', base=Client)
    bytestopic = run_agent('bytestopic', base=Client)

    # Connect clients
    addr = server.addr('publish')
    addr_both = both.connect(addr, handler={'positive': append_received,
                                            'negative': append_received})
    addr_positive = positive.connect(addr,
                                     handler={'positive': append_received})
    addr_bytestopic = bytestopic.connect(addr,
                                         handler={b'\xeb': append_received})
    assert addr_both == addr.twin()
    assert addr_positive == addr.twin()
    assert addr_bytestopic == addr.twin()

    # Publish from server
    server.each(0, 'publish_str')

    # Wait for clients to receive some data
    N = 10
    assert wait_agent_attr(both, length=N)
    assert wait_agent_attr(positive, length=N)
    assert wait_agent_attr(bytestopic, length=N)

    # both
    received = [int(x) for x in both.get_attr('received')]
    assert len(received) >= N
    for i in range(1, len(received)):
        if received[i] > 0:
            assert received[i - 1] == 1 - received[i]
        else:
            assert received[i - 1] == -received[i]

    # positive
    received = [int(x) for x in positive.get_attr('received')]
    assert len(received) >= N
    assert received == list(range(received[0], received[-1] + 1))

    # bytestopic
    received = bytestopic.get_attr('received')
    assert len(received) >= N
    assert all(x == 'bytes...' for x in received)


@pytest.mark.parametrize('server', [Server, ServerYield])
def test_request(nsproxy, server):
    """
    Synchronous publish-subscribe pattern with a client that makes a request.

    In this test there is one SYNC_PUB server and two SYNC_SUB clients. The
    server is publishing messages when one of the clients makes a request.
    The response to that request must only be received by the requester.

    It also verifies that the response is processed by the client with a
    different handler, which must be set for each request sent to the
    publisher.
    """
    server = run_agent('server', base=server)
    active = run_agent('active_client', base=Client)
    passive = run_agent('passive_client', base=Client)

    # Connect clients
    server_addr = server.addr('publish')
    active_addr = active.connect(server_addr, alias='sub',
                                 handler=append_received)
    passive_addr = passive.connect(server_addr, alias='sub',
                                   handler=append_received)
    assert active_addr == server_addr.twin()
    assert passive_addr == server_addr.twin()

    # Publish from server
    server.each(0, 'publish')

    # Wait for clients to receive some data
    N = 10
    assert wait_agent_attr(active, length=N)
    assert wait_agent_attr(passive, length=N)

    # Send request from active client
    active.send('sub', 'request!', handler=receive_negate)

    # Server request processing
    assert wait_agent_attr(server, length=1)
    received = server.get_attr('received')
    assert len(received) == 1
    assert received[0][1] == 'request!'
    instant = received[0][0]

    # Make sure active gets response
    response = instant + 0.5
    assert wait_agent_attr(active, data=-response)

    # Wait for at least another message after the response
    N = len(active.get_attr('received')) + 1
    assert wait_agent_attr(active, length=N)

    # Check received messages are properly sorted
    received = active.get_attr('received')
    index = received.index(-response)
    assert received[index - 1] + 1 == received[index + 1]
    received.remove(-response)
    assert received == list(range(received[0], received[-1] + 1))

    # Check passive client received data
    assert wait_agent_attr(passive, data=received[-1])
    received = passive.get_attr('received')
    assert -response not in received
    assert received == list(range(received[0], received[-1] + 1))


def test_wait(nsproxy):
    """
    Asynchronous request-reply pattern maximum wait.

    When a client makes a request, it can also set a maximum wait time and
    a function to be executed in case the message is not received after that
    period.
    """
    server = run_agent('server', base=ServerLate)
    client = run_agent('client', base=Client)
    logger = run_logger('logger')
    client.set_logger(logger)
    sync_agent_logger(client, logger)

    # Connect clients
    server_addr = server.addr('publish')
    client.connect(server_addr, alias='sub', handler=append_received)

    # Publish from server
    server.each(0, 'publish')

    # Wait for client to receive some data
    N = 10
    assert wait_agent_attr(client, length=N)

    # Response received in time
    fast = 0
    client.send('sub', fast, handler=append_received, wait=0.5)
    time.sleep(0.2)
    assert server.get_attr('received') == [fast]
    assert 'x' + str(fast) in client.get_attr('received')

    # Response not received in time
    slow = 1
    client.send('sub', slow, handler=append_received, wait=0.1)
    assert logger_received(logger,
                           log_name='log_history_warning',
                           message='not receive req',
                           timeout=0.5)
    assert server.get_attr('received') == [fast, slow]
    assert 'x' + str(slow) not in client.get_attr('received')

    # Response not received in time with error handler
    slow = 1
    client.send('sub', slow, handler=append_received, wait=0.1,
                on_error=on_error)
    assert wait_agent_attr(client, name='error_log', length=1, timeout=0.5)
    assert server.get_attr('received') == [fast, slow]
    assert 'x' + str(slow) not in client.get_attr('received')
