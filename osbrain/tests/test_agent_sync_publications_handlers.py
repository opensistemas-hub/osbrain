'''
Test file for synchronized publications handlers.
'''
import pytest

from osbrain import Agent
from osbrain import run_agent
from osbrain.helper import wait_agent_attr

from common import nsproxy  # noqa: F401
from common import append_received


class ServerSyncPub(Agent):
    def on_init(self):
        self.received = []
        self.bind('SYNC_PUB', alias='publish', handler='reply')

    def reply(self, request):
        self.received.append(request)
        return 'reply!'

    def publish(self):
        self.send('publish', 'publication!')


class ClientWithHandler(Agent):
    def on_init(self):
        self.received = []
        self.alternative_received = []

    def receive_method(self, response):
        self.received.append(response)

    def alternative_receive(self, response):
        self.alternative_received.append(response)


def test_sync_pub_handler_exists(nsproxy):
    '''
    When binding a SYNC_PUB socket without a handler, an exception must be
    thrown, letting the user know that a handler must be specified.
    '''
    server = run_agent('server', base=Agent)

    with pytest.raises(ValueError) as error:
        server.bind('SYNC_PUB', alias='should_crash')
    assert 'This socket requires a handler!' in str(error.value)


@pytest.mark.parametrize(
    'handler',
    ['reply', append_received, lambda a, x: a.received.append(x)]
)
def test_sync_pub_handler_types(nsproxy, handler):
    '''
    When binding a SYNC_PUB socket, we must accept different types of
    handlers: methods, functions, lambda expressions...
    '''
    server = run_agent('server', base=ServerSyncPub)

    assert server.bind('SYNC_PUB', alias='should_not_crash',
                       handler=handler)


@pytest.mark.parametrize(
    'handler, check_function',
    [('receive_method', False),
     (append_received, True),
     (lambda a, x: a.received.append(x), False)])
def test_sync_pub_connect_handler_types(nsproxy, handler, check_function):
    '''
    The handler for the normal PUB/SUB communication is specified in the
    `connect` call.

    We should be able to specify this in various ways: method, functions,
    lambda expressions...
    '''
    server = run_agent('server', base=ServerSyncPub)
    client = run_agent('client', base=ClientWithHandler)

    addr = server.addr('publish')

    client.connect(addr, alias='sub', handler=handler)
    server.each(0.01, 'publish')
    assert wait_agent_attr(client, length=2, data='publication!')

    if check_function:
        # Check that the function was not stored as a method for the object
        with pytest.raises(AttributeError) as error:
            assert client.get_attr('append_received')
        assert 'object has no attribute' in str(error.value)


@pytest.mark.parametrize(
    'handler, check_function, should_crash',
    [('receive_method', False, False),
     (append_received, True, False),
     (lambda a, x: a.received.append(x), False, False),
     (None, False, True)])
def test_sync_pub_send_handlers(nsproxy, handler, check_function,
                                should_crash):
    '''
    The handler for the requests MUST be specified in the `send` call.
    It can be specified in different ways: method, functions...
    '''
    server = run_agent('server', base=ServerSyncPub)
    client = run_agent('client', base=ClientWithHandler)

    addr = server.addr('publish')

    # Use an alternative handler so as to guarantee connection is established
    client.connect(addr, alias='sub', handler='alternative_receive')
    server.each(0.01, 'publish')
    assert wait_agent_attr(client, name='alternative_received', length=2,
                           data='publication!')

    if should_crash:
        with pytest.raises(ValueError):
            client.send('sub', 'request!')
    else:
        client.send('sub', 'request!', handler=handler)
        assert wait_agent_attr(client, length=1)

        if check_function:
            # Check that the function was not stored as a method for the object
            with pytest.raises(AttributeError) as error:
                assert client.get_attr('append_received')
            assert 'object has no attribute' in str(error.value)
