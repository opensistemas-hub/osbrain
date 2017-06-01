'''
Test file for asynchronous requests handlers.
'''
import time

import pytest

from osbrain import Agent
from osbrain import run_agent

from common import nsproxy  # pragma: no flakes


class Server_ASYNC_REP(Agent):
    def on_init(self):
        self.received = []
        self.bind('ASYNC_REP', alias='publish', handler='reply')

    def reply(self, request):
        self.received.append(request)
        return 'reply!'


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
    We should be able to specify the handler in the `connect` call in
    different ways: method, functions, lambda expressions...

    Note that this handler will be used if not overriden by the `handler`
    parameter in the `send` call. However, that is specifically checked in
    other test.
    '''
    handler, check_function = params

    server = run_agent('server', base=Server_ASYNC_REP)
    client = run_agent('client', base=ClientWithHandler)

    addr = server.addr('publish')

    client.connect(addr, alias='sub', handler=handler)
    client.send('sub', 'request!')
    time.sleep(1)
    assert len(client.get_attr('received')) == 1

    if check_function:
        # Check that the function was not stored as a method for the object
        with pytest.raises(Exception):
            assert client.get_attr('receive_function')


@pytest.mark.parametrize(
    'params',
    [('receive_method', False),
     (receive_function, True),
     (lambda a, x: a.received.append(x), False)])
def test_send_handler_types(nsproxy, params):
    '''
    We should be able to override the handler in the `send` call in
    different ways: method, functions...
    '''
    handler, check_function = params

    server = run_agent('server', base=Server_ASYNC_REP)
    client = run_agent('client', base=ClientWithHandler)

    addr = server.addr('publish')

    # Default handler should not be called when specifying a handler on `send`
    client.connect(addr, alias='sub', handler='crash_handler')

    client.send('sub', 'request!', handler=handler)
    time.sleep(1)
    assert len(client.get_attr('received')) == 1

    if check_function:
        # Check that the function was not stored as a method for the object
        with pytest.raises(Exception):
            assert client.get_attr('receive_function')
