"""
Test file for asynchronous requests.
"""
import time

from osbrain import run_agent
from osbrain import run_logger

from common import nsproxy  # pragma: no flakes
from common import sync_agent_logger
from common import logger_received


def test_return(nsproxy):
    """
    Asynchronous request-reply pattern with a reply handler that returns.
    """
    def late_reply(agent, request):
        agent.received.append(request)
        time.sleep(1)
        return 'x' + request

    def receive(agent, response):
        agent.received.append(response)

    server = run_agent('server')
    client = run_agent('client')
    server.set_attr(received=[])
    client.set_attr(received=[])

    addr = server.bind('ASYNC_REP', alias='replier', handler=late_reply)
    client.connect(addr, alias='async', handler=receive)

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

    def receive(agent, response):
        agent.received.append(response)

    server = run_agent('server')
    client = run_agent('client')
    server.set_attr(received=[])
    client.set_attr(received=[])

    addr = server.bind('ASYNC_REP', alias='replier', handler=late_reply)
    client.connect(addr, alias='async', handler=receive)

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


def test_unknown(nsproxy):
    """
    When receiving a response for an unknow request (or an already processed
    request), a warning should be logged and handler should not be executed.
    """
    def late_reply(agent, request):
        agent.received.append(request)
        time.sleep(1)
        return 'x' + request

    def receive(agent, response):
        agent.received.append(response)

    server = run_agent('server')
    client = run_agent('client')
    logger = run_logger('logger')
    server.set_attr(received=[])
    client.set_attr(received=[])
    client.set_logger(logger)
    sync_agent_logger(client, logger)

    addr = server.bind('ASYNC_REP', alias='replier', handler=late_reply)
    client.connect(addr, alias='async', handler=receive)
    client.send('async', 'foo')

    # Manually remove the pending request before it is received
    client.set_attr(_pending_requests={})
    time.sleep(1.1)
    assert server.get_attr('received') == ['foo']
    assert client.get_attr('received') == []
    assert logger_received(logger,
                           log_name='log_history_warning',
                           message='Received response for an unknown request!')


def test_wait(nsproxy):
    """
    Asynchronous request-reply pattern maximum wait.
    """
    def late_reply(agent, delay):
        agent.received.append(delay)
        time.sleep(delay)
        return 'x' + str(delay)

    def receive(agent, response):
        agent.received.append(response)

    server = run_agent('server')
    client = run_agent('client')
    logger = run_logger('logger')
    server.set_attr(received=[])
    client.set_attr(received=[])
    client.set_logger(logger)
    sync_agent_logger(client, logger)

    addr = server.bind('ASYNC_REP', alias='replier', handler=late_reply)
    client.connect(addr, alias='async', handler=receive)

    # Response received in time
    client.send('async', 1, wait=2)
    time.sleep(1.1)
    assert server.get_attr('received') == [1]
    assert client.get_attr('received') == ['x1']

    # Response not received in time
    client.send('async', 2, wait=1)
    assert logger_received(logger,
                           log_name='log_history_warning',
                           message='not receive req',
                           timeout=1.1)
    assert server.get_attr('received') == [1, 2]
    assert client.get_attr('received') == ['x1']


def test_wait_on_error(nsproxy):
    """
    Asynchronous request-reply pattern maximum wait with an error handler.
    """
    def on_error(agent):
        agent.error_count += 1

    def late_reply(agent, delay):
        agent.received.append(delay)
        time.sleep(delay)
        return 'x' + str(delay)

    def receive(agent, response):
        agent.received.append(response)

    server = run_agent('server')
    client = run_agent('client')
    server.set_attr(received=[])
    client.set_attr(received=[])
    client.set_attr(error_count=0)

    addr = server.bind('ASYNC_REP', alias='replier', handler=late_reply)
    client.connect(addr, alias='async', handler=receive)

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
