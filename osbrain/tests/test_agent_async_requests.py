"""
Test file for asynchronous requests.
"""
import time

from osbrain import run_agent
from osbrain import Agent
from osbrain import run_logger
from osbrain.helper import sync_agent_logger
from osbrain.helper import logger_received
from osbrain.helper import wait_agent_attr

from .common import nsproxy  # noqa: F401
from .common import append_received


def on_error(agent):
    agent.error_count += 1


class Server(Agent):
    def on_init(self):
        self.received = []
        self.blocked = False


class Client(Agent):
    def on_init(self):
        self.received = []


def blocked_reply(agent, request):
    agent.blocked = True
    agent.received.append(request)
    while agent.blocked:
        time.sleep(.01)

    return 'x' + request


def async_client_server(server_handler=blocked_reply):
    server = run_agent('server', base=Server)
    client = run_agent('client', base=Client)

    addr = server.bind('ASYNC_REP', alias='replier', handler=server_handler)
    client.connect(addr, alias='async', handler=append_received)

    return (client, server)


def async_client_server_pair(server_handler=blocked_reply):
    client, server1 = async_client_server(server_handler)

    server2 = run_agent('server2', base=Server)
    addr2 = server2.bind('ASYNC_REP', alias='replier2', handler=server_handler)
    client.connect(addr2, alias='async2', handler=append_received)

    return (client, server1, server2)


def test_return(nsproxy):
    """
    Asynchronous request-reply pattern with a reply handler that returns.
    """
    client, server1, server2 = async_client_server_pair()
    client.send('async', 'foo')
    client.send('async', 'bar')
    client.send('async2', 'qux')

    assert wait_agent_attr(server1, value=['foo'], timeout=.1)
    assert wait_agent_attr(server2, value=['qux'], timeout=.1)
    assert not wait_agent_attr(client, length=1, timeout=.1)

    server2.unsafe.set_attr(blocked=False)
    assert wait_agent_attr(client, value=['xqux'], timeout=.1)

    server1.unsafe.set_attr(blocked=False)
    assert wait_agent_attr(client, value=['xqux', 'xfoo'], timeout=.1)
    server1.unsafe.set_attr(blocked=False)
    assert wait_agent_attr(client, value=['xqux', 'xfoo', 'xbar'], timeout=.1)


def test_yield(nsproxy):
    """
    Asynchronous request-reply pattern with a reply handler that yields.
    """
    def blocked_reply_yield(agent, request):
        agent.received.append(request)
        agent.blocked = True
        while agent.blocked:
            time.sleep(.01)

        yield 'x' + request
        agent.received.append('y' + request)

    client, server1, server2 = async_client_server_pair(blocked_reply_yield)
    client.send('async', 'foo')
    client.send('async2', 'bar')

    assert wait_agent_attr(server1, value=['foo'], timeout=.1)
    assert wait_agent_attr(server2, value=['bar'], timeout=.1)
    assert not wait_agent_attr(client, length=1, timeout=.1)

    server2.unsafe.set_attr(blocked=False)
    assert wait_agent_attr(client, value=['xbar'], timeout=.1)
    assert wait_agent_attr(server2, value=['bar', 'ybar'], timeout=.1)

    server1.unsafe.set_attr(blocked=False)
    assert wait_agent_attr(client, value=['xbar', 'xfoo'], timeout=.1)
    assert wait_agent_attr(server1, value=['foo', 'yfoo'], timeout=.1)


def test_unknown(nsproxy):
    """
    When receiving a response for an unknown request (or an already processed
    request), a warning should be logged and handler should not be executed.
    """
    client, server = async_client_server()

    logger = run_logger('logger')
    client.set_logger(logger)
    sync_agent_logger(client, logger)

    client.send('async', 'foo')
    assert wait_agent_attr(server, value=['foo'], timeout=.1)

    # Manually remove the pending request before it is received
    client.set_attr(_pending_requests={})
    server.unsafe.set_attr(blocked=False)
    assert logger_received(logger,
                           log_name='log_history_warning',
                           message='Received response for an unknown request!')
    assert len(client.get_attr('received')) == 0


def test_wait_in_time(nsproxy):
    """
    Asynchronous request-reply pattern maximum wait.
    """
    client, server = async_client_server()

    logger = run_logger('logger')
    client.set_logger(logger)
    sync_agent_logger(client, logger)

    client.send('async', 'foo', wait=1)
    assert wait_agent_attr(server, value=['foo'])
    server.unsafe.set_attr(blocked=False)
    assert wait_agent_attr(client, value=['xfoo'])


def test_wait_timeout(nsproxy):
    """
    Asynchronous request-reply pattern when exceeding the maximum wait.
    """
    client, server = async_client_server()
    logger = run_logger('logger')
    client.set_logger(logger)
    sync_agent_logger(client, logger)

    client.send('async', 'foo', wait=.5)
    assert len(client.get_attr('_pending_requests')) == 1
    assert logger_received(logger,
                           log_name='log_history_warning',
                           message='not receive req',
                           timeout=1)
    assert len(client.get_attr('_pending_requests')) == 0

    server.unsafe.set_attr(blocked=False)
    assert logger_received(logger,
                           log_name='log_history_warning',
                           message='Received response for an unknown request!')
    assert server.get_attr('received') == ['foo']
    assert client.get_attr('received') == []


def test_wait_on_error(nsproxy):
    """
    Asynchronous request-reply pattern maximum wait with an error handler.
    """
    client, server = async_client_server()

    client.set_attr(error_count=0)
    client.send('async', 'foo', wait=.5, on_error=on_error)
    assert wait_agent_attr(client, 'error_count', value=1, timeout=1)
    server.unsafe.set_attr(blocked=False)
