"""
Test file for asynchronous requests.
"""
import time

from osbrain import run_agent

from common import nsproxy  # pragma: no flakes


# addr = server.bind('PULL', alias='replier', handler=foo)
# client.connect(addr)
#
# # When binding, a PULL socket is created (to recieve all requests),
# # requests are handled with the same handler
# addr = server.bind('ASYNC_REP', alias='replier', handler=foo)
# # When connecting to an ASYNC_REP some things happen:
# #  - A PUSH socket is created with an alias
# #  - Client UUID is sent, along with a PULL AgentAddress, so the server
# #    knows where to send requests that come from that agent. Should a new
# #    PULL socket be created instead for each connection?
# client.connect(addr, alias='async')
# #  - Send will have a special send_async_req case
# #  - handler, wait, repeat, on_error could have default values set on connect()
# #  - send will add UUID of the agent and an UUID for the request
# #  - a timer is created to wait for the response before raising...
# client.send('async', 'a request here...',
#             handler=bar, wait=3, on_error=omg)
# # For PUB-SUB there will be another special AddressKind (i.e.: STREAM?),
# #  - A SUB socket is created with an alias
# client.send('sync', 'a request here...',
#             handler=bar, wait=3, repeat=2, on_error=omg)


def test_return(nsproxy):
    """
    Asynchronous request-reply pattern with a reply handler that returns.
    """
    def late_reply(agent, message):
        agent.received.append(message)
        time.sleep(1)
        return message

    def receive(agent, message):
        agent.received.append('x' + message)

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
    received = client.get_attr('received')
    assert server.get_attr('received') == ['foo', 'bar']
    assert client.get_attr('received') == ['xfoo', 'xbar']


def test_yield(nsproxy):
    """
    Asynchronous request-reply pattern with a reply handler that yields.
    """
    def late_reply(agent, message):
        agent.received.append(message)
        time.sleep(1)
        yield message
        agent.received.append(message)

    def receive(agent, message):
        agent.received.append('x' + message)

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
    assert server.get_attr('received') == ['foo', 'foo', 'bar']
    assert client.get_attr('received') == ['xfoo']
    time.sleep(1)
    received = client.get_attr('received')
    assert server.get_attr('received') == ['foo', 'foo', 'bar', 'bar']
    assert client.get_attr('received') == ['xfoo', 'xbar']


def test_wait(nsproxy):
    # TODO
    #client.send('async', 'Hello world!', wait=3)
    pass


def test_wait_on_error(nsproxy):
    def on_error(agent):
        pass
    # TODO
    #client.send('async', 'Hello world!', wait=3, on_error=on_error)
    pass
