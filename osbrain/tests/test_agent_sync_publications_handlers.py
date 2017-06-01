'''
Test file for synchronized publications handlers.
'''
import time

import pytest

from osbrain import Agent
from osbrain import run_agent

from common import nsproxy  # pragma: no flakes


class Server_SYNC_PUB(Agent):
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

    def crash_handler(self, response):
        raise Exception()

    def receive_method(self, response):
        self.received.append(response)


def receive_function(agent, response):
    agent.received.append(response)


@pytest.mark.parametrize(
    'params',
    [('receive_method', False),
     (receive_function, True),
     (lambda a, x: a.received.append(x), False)])
def test_connect_handler_types(nsproxy, params):
    '''
    The handler for the normal PUB/SUB communication is specified in the
    `connect` call.

    We should be able to specify this in various ways: method, functions,
    lambda expressions...
    '''
    handler, check_function = params

    server = run_agent('server', base=Server_SYNC_PUB)
    client = run_agent('client', base=ClientWithHandler)

    addr = server.addr('publish')

    client.connect(addr, alias='sub', handler=handler)
    server.publish()
    time.sleep(1)
    assert len(client.get_attr('received')) == 1

    if check_function:
        # Check that the function was not stored as a method for the object
        with pytest.raises(Exception):
            assert client.get_attr('receive_function')


@pytest.mark.parametrize(
    'params',
    [('receive_method', False, False),
     (receive_function, True, False),
     (lambda a, x: a.received.append(x), False, False),
     (None, False, True)])
def test_sync_pub_send_handlers(nsproxy, params):
    '''
    The handler for the requests MUST be specified in the `send` call.
    It can be specified in different ways: method, functions...
    '''
    handler, check_function, should_crash = params

    server = run_agent('server', base=Server_SYNC_PUB)
    client = run_agent('client', base=ClientWithHandler)

    addr = server.addr('publish')

    # PUB/SUB handler should not be used in the requests at all
    client.connect(addr, alias='sub', handler='crash_handler')

    if should_crash:
        with pytest.raises(ValueError):
            client.send('sub', 'request!')
    else:
        client.send('sub', 'request!', handler=handler)
        time.sleep(1)
        assert len(client.get_attr('received')) == 1

        if check_function:
            # Check that the function was not stored as a method for the object
            with pytest.raises(Exception):
                assert client.get_attr('receive_function')
