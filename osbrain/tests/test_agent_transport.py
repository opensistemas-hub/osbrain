"""
Test file for communication transport.
"""
import os
import random
from shutil import rmtree
from tempfile import mkdtemp
from uuid import uuid4

import osbrain
from osbrain import Agent
from osbrain import run_agent
from osbrain import SocketAddress
from osbrain.helper import wait_agent_attr

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
    assert address.address.name == ipc_addr
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


def test_agent_ipc_from_different_folders(nsproxy):
    """
    IPC should work well even when agents are run from different folders.
    """
    class Wdagent(Agent):
        def on_init(self):
            self.received = []

    def receive(agent, message):
        agent.received.append(message)

    dira = mkdtemp()
    dirb = mkdtemp()
    assert dira != dirb

    # First agent run for directory `a`
    os.chdir(dira)
    a = run_agent('a', base=Wdagent)
    random_addr = a.bind('PULL', transport='ipc', handler=receive)
    set_addr = a.bind('PULL', addr='qwer', transport='ipc', handler=receive)

    # Second agent run for directory `b`
    os.chdir(dirb)
    b = run_agent('b', base=Wdagent)
    b.connect(random_addr, alias='random')
    b.connect(set_addr, alias='set')
    b.send('random', 'foo')
    b.send('set', 'bar')

    # Wait for `a` to receive the message
    random_received = wait_agent_attr(a, data='foo', timeout=1)
    set_received = wait_agent_attr(a, data='bar', timeout=1)

    # Clean directories
    rmtree(dira)
    rmtree(dirb)

    assert random_received
    assert set_received
