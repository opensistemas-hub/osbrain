"""
Test file for asynchronous requests.
"""
import time

import pytest

from osbrain import run_agent
from osbrain import Agent
from osbrain import run_logger
from osbrain.helper import sync_agent_logger
from osbrain.helper import logger_received

from common import nsproxy  # noqa: F401
from common import append_received


def on_error(agent):
    agent.error_count += 1


class Server(Agent):
    def on_init(self):
        self.received = []


class Client(Agent):
    def on_init(self):
        self.received = []


@pytest.fixture(scope='function')
def server_client_late_reply_return():
    def late_reply(agent, request):
        agent.received.append(request)
        time.sleep(1)
        return 'x' + request

    server = run_agent('server', base=Server)
    client = run_agent('client', base=Client)

    addr = server.bind('ASYNC_REP', alias='replier', handler=late_reply)
    client.connect(addr, alias='async', handler=append_received)

    return (server, client)


@pytest.fixture(scope='function')
def server_client_late_reply_delay():
    def late_reply(agent, delay):
        agent.received.append(delay)
        time.sleep(delay)
        return 'x' + str(delay)

    server = run_agent('server', base=Server)
    client = run_agent('client', base=Client)

    addr = server.bind('ASYNC_REP', alias='replier', handler=late_reply)
    client.connect(addr, alias='async', handler=append_received)

    return (server, client)


def test_return(nsproxy, server_client_late_reply_return):
    """
    Asynchronous request-reply pattern with a reply handler that returns.
    """

    server, client = server_client_late_reply_return

    # Client requests should be non-blocking
    t0 = time.time()
    client.send('async', 'foo')
    client.send('async', 'bar')
    assert time.time() - t0 < 0.1

    # Server should receive first request "soon"
    time.sleep(0.1)
    assert server.get_attr('received') == ['foo']
    assert client.get_attr('received') == []

    # Wait for client to receive reply asynchronously
    time.sleep(1)
    assert server.get_attr('received') == ['foo', 'bar']
    assert client.get_attr('received') == ['xfoo']
    time.sleep(1)
    assert server.get_attr('received') == ['foo', 'bar']
    assert client.get_attr('received') == ['xfoo', 'xbar']


def test_yield(nsproxy):
    """
    Asynchronous request-reply pattern with a reply handler that yields.
    """
    def late_reply(agent, request):
        agent.received.append(request)
        time.sleep(1)
        yield 'x' + request
        agent.received.append('y' + request)

    server = run_agent('server', base=Server)
    client = run_agent('client', base=Client)

    addr = server.bind('ASYNC_REP', alias='replier', handler=late_reply)
    client.connect(addr, alias='async', handler=append_received)

    # Client requests should be non-blocking
    t0 = time.time()
    client.send('async', 'foo')
    client.send('async', 'bar')
    assert time.time() - t0 < 0.1

    # Server should receive first request "soon"
    time.sleep(0.1)
    assert server.get_attr('received') == ['foo']
    assert client.get_attr('received') == []

    # Wait for client to receive reply asynchronously
    time.sleep(1)
    assert server.get_attr('received') == ['foo', 'yfoo', 'bar']
    assert client.get_attr('received') == ['xfoo']
    time.sleep(1)
    assert server.get_attr('received') == ['foo', 'yfoo', 'bar', 'ybar']
    assert client.get_attr('received') == ['xfoo', 'xbar']


def test_unknown(nsproxy, server_client_late_reply_return):
    """
    When receiving a response for an unknown request (or an already processed
    request), a warning should be logged and handler should not be executed.
    """
    server, client = server_client_late_reply_return

    logger = run_logger('logger')
    client.set_logger(logger)
    sync_agent_logger(client, logger)

    client.send('async', 'foo')

    # Manually remove the pending request before it is received
    client.set_attr(_pending_requests={})
    time.sleep(1.1)
    assert server.get_attr('received') == ['foo']
    assert client.get_attr('received') == []
    assert logger_received(logger,
                           log_name='log_history_warning',
                           message='Received response for an unknown request!')


def test_wait(nsproxy, server_client_late_reply_delay):
    """
    Asynchronous request-reply pattern maximum wait.
    """
    server, client = server_client_late_reply_delay

    logger = run_logger('logger')
    client.set_logger(logger)
    sync_agent_logger(client, logger)

    # Response received in time
    client.send('async', 1, wait=2)
    time.sleep(1.1)
    assert server.get_attr('received') == [1]
    assert client.get_attr('received') == ['x1']

    # Response not received in time
    client.send('async', 2, wait=1)
    assert len(client.get_attr('_pending_requests')) == 1
    assert logger_received(logger,
                           log_name='log_history_warning',
                           message='not receive req',
                           timeout=1.1)

    assert logger_received(logger,
                           log_name='log_history_warning',
                           message='Received response for an unknown request!',
                           timeout=2)
    assert len(client.get_attr('_pending_requests')) == 0
    assert server.get_attr('received') == [1, 2]
    assert client.get_attr('received') == ['x1']


def test_wait_on_error(nsproxy, server_client_late_reply_delay):
    """
    Asynchronous request-reply pattern maximum wait with an error handler.
    """
    server, client = server_client_late_reply_delay

    client.set_attr(error_count=0)

    # Response received in time
    client.send('async', 1, wait=2)
    time.sleep(1.1)
    assert server.get_attr('received') == [1]
    assert client.get_attr('received') == ['x1']

    # Response not received in time
    client.send('async', 2, wait=1, on_error=on_error)
    time.sleep(1.1)
    assert client.get_attr('error_count') == 1
    assert client.get_attr('received') == ['x1']
