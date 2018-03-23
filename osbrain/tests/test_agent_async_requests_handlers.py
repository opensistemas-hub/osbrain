'''
Test file for asynchronous requests handlers.
'''
import pytest

from osbrain import Agent
from osbrain import run_agent
from osbrain.helper import wait_agent_attr

from common import nsproxy  # noqa: F401
from common import append_received


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


def test_async_rep_handler_exists(nsproxy):
    '''
    When binding an ASYNC_REP socket without a handler, an exception must be
    thrown, letting the user know that a handler must be specified.
    '''
    server = run_agent('server', base=Agent)

    with pytest.raises(ValueError) as error:
        server.bind('ASYNC_REP', alias='should_crash')
    assert 'This socket requires a handler!' in str(error.value)


@pytest.mark.parametrize(
    'handler',
    ['reply', append_received, lambda a, x: a.received.append(x)]
)
def test_async_rep_handler_types(nsproxy, handler):
    '''
    When binding an ASYNC_REP socket, we must accept different types of
    handlers: methods, functions, lambda expressions...
    '''
    server = run_agent('server', base=Server_ASYNC_REP)

    assert server.bind('ASYNC_REP', alias='should_not_crash',
                       handler=handler)


@pytest.mark.parametrize(
    'handler, check_function',
    [('receive_method', False),
     (append_received, True),
     (lambda a, x: a.received.append(x), False)])
def test_async_rep_connect_handler_types(nsproxy, handler, check_function):
    '''
    We should be able to specify the handler in the `connect` call in
    different ways: method, functions, lambda expressions...

    Note that this handler will be used if not overriden by the `handler`
    parameter in the `send` call. However, that is specifically checked in
    other test.
    '''
    server = run_agent('server', base=Server_ASYNC_REP)
    client = run_agent('client', base=ClientWithHandler)

    addr = server.addr('publish')

    client.connect(addr, alias='sub', handler=handler)
    client.send('sub', 'request!')
    assert wait_agent_attr(client, length=1)

    if check_function:
        # Check that the function was not stored as a method for the object
        with pytest.raises(AttributeError) as error:
            assert client.get_attr('append_received')
        assert 'object has no attribute' in str(error.value)


@pytest.mark.parametrize(
    'handler, check_function',
    [('receive_method', False),
     (append_received, True),
     (lambda a, x: a.received.append(x), False)])
def test_async_rep_send_handler_types(nsproxy, handler, check_function):
    '''
    We should be able to make requests even if we do not specify a handler
    on the `connect` call, as long as we specify it on the `send` call.
    '''
    server = run_agent('server', base=Server_ASYNC_REP)
    client = run_agent('client', base=ClientWithHandler)

    addr = server.addr('publish')

    # Connect without a handler
    client.connect(addr, alias='sub')

    client.send('sub', 'request!', handler=handler)
    assert wait_agent_attr(client, length=1)

    if check_function:
        # Check that the function was not stored as a method for the object
        with pytest.raises(AttributeError) as error:
            assert client.get_attr('append_received')
        assert 'object has no attribute' in str(error.value)
