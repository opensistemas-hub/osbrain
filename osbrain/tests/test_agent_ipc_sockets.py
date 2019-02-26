"""
Test file for everything IPC socket related
"""
import pytest

from osbrain import run_agent
from osbrain import run_nameserver
from osbrain.helper import agent_dies
from osbrain.helper import wait_condition

from .common import nsproxy  # noqa: F401
from .common import skip_windows_ipc

pytestmark = skip_windows_ipc


def test_agent_close_ipc_socket_agent_shutdown(nsproxy):
    """
    Check that the socket is closed and the socket file removed after the agent
    is shut down.
    """
    agent = run_agent('name')
    address = agent.bind('PUSH')
    agent.shutdown()

    assert agent_dies('name', nsproxy)
    assert wait_condition(address.address.exists, negate=True)


def test_agent_close_ipc_socket_agent_kill(nsproxy):
    """
    Check that the socket is closed and the socket file removed after the agent
    is killed.
    """
    agent = run_agent('name')
    address = agent.bind('PUSH')
    agent.oneway.kill()

    assert agent_dies('name', nsproxy)
    assert wait_condition(address.address.exists, negate=True)


def test_agent_close_ipc_socket_agent_blocked_nameserver_shutdown():
    """
    Check that the socket is closed and the socket file removed when the name
    server is shut down having a blocked agent.
    """
    def block(agent):
        agent.send('out', 'blocking...')

    ns = run_nameserver()
    blocker = run_agent('blocker')
    blocker.set_method(block)
    addr = blocker.bind('PUSH', alias='out')
    blocker.after(0, 'block')
    ns.shutdown(timeout=1.)

    assert wait_condition(addr.address.exists, negate=True)


def test_agent_close_ipc_socket_agent_crash_nameserver_shutdown():
    """
    Check that the socket is closed and the socket file removed after the agent
    crashes and the name server calls for shutdown.
    """
    ns = run_nameserver()
    agent = run_agent('agent')
    addr = agent.bind('PUSH', 'main')
    with pytest.raises(RuntimeError):
        agent.raise_exception()

    ns.shutdown()

    assert wait_condition(addr.address.exists, negate=True)


def test_agent_close_ipc_socket_nameserver_shutdown():
    """
    Check that the socket is closed and the socket file removed after the name
    server is shut down.
    """
    ns = run_nameserver()
    agent = run_agent('agent')
    addr = agent.bind('PUSH', 'main')
    ns.shutdown()

    assert wait_condition(addr.address.exists, negate=True)
