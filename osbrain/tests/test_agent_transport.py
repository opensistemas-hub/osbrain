"""
Test file for communication transport.
"""
import random
from uuid import uuid4

import osbrain
from osbrain import run_agent
from osbrain import SocketAddress

from common import nsproxy  # pragma: no flakes


def test_agent_bind_transport_global(nsproxy):
    """
    Test global default transport.
    """
    # Default transport
    agent = run_agent('a0')
    address = agent.bind('PUSH')
    assert address.transport == 'ipc'

    # Changing default global transport
    osbrain.config['TRANSPORT'] = 'tcp'
    agent = run_agent('a1')
    address = agent.bind('PUSH')
    assert address.transport == 'tcp'

    osbrain.config['TRANSPORT'] = 'ipc'
    agent = run_agent('a2')
    address = agent.bind('PUSH')
    assert address.transport == 'ipc'


def test_agent_bind_transport_agent(nsproxy):
    """
    Test agent default transport.
    """
    agent = run_agent('a0', transport='tcp')
    address = agent.bind('PUSH')
    assert address.transport == 'tcp'

    agent = run_agent('a1', transport='ipc')
    address = agent.bind('PUSH')
    assert address.transport == 'ipc'


def test_agent_bind_transport_bind(nsproxy):
    """
    Test bind transport.
    """
    agent = run_agent('a0')

    address = agent.bind('PUSH', transport='tcp')
    assert address.transport == 'tcp'

    address = agent.bind('PUSH', transport='inproc')
    assert address.transport == 'inproc'


def test_agent_bind_given_address(nsproxy):
    """
    Test agent binding to an specified address using TCP and IPC transport
    layers.
    """
    agent = run_agent('a0')
    # IPC
    ipc_addr = str(uuid4())
    address = agent.bind('PUSH', addr=ipc_addr, transport='ipc')
    assert address.transport == 'ipc'
    assert address.address == ipc_addr
    # TCP
    while True:
        try:
            # Bind to random port
            port = random.randrange(10000, 20000)
            tcp_addr = '127.0.0.1:%s' % port
            tcp_addr = SocketAddress('127.0.0.1', port)
            address = agent.bind('PUSH', addr=tcp_addr, transport='tcp')
            break
        except Exception:
            pass
    assert address.transport == 'tcp'
    assert address.address == tcp_addr
