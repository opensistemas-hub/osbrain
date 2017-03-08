"""
Test file for asynchronous requests.
"""
import time

from osbrain import run_agent

from common import nsproxy  # pragma: no flakes


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
    assert time.time() - t0 < 0.01

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
    assert time.time() - t0 < 0.01

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


def test_wait(nsproxy):
    # TODO
    # client.send('async', 'Hello world!', wait=3)
    pass


def test_wait_on_error(nsproxy):
    def on_error(agent):
        pass
    # TODO
    # client.send('async', 'Hello world!', wait=3, on_error=on_error)
    pass
