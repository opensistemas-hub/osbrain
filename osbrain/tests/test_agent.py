import pytest
import random
import copy
import multiprocessing

from osbrain.core import TryREQ
from osbrain.core import Agent
from osbrain.core import AgentSock
from osbrain.core import AgentRPP
from osbrain.message import Message
from osbrain.message import Types as mType


class FastPublisher(Agent):
    def __init__(self, rpp=AgentRPP(), queue=None):
        Agent.__init__(self, rpp, queue)
        self.poll_timeout = 0.001
        self.memory['a'] = 0
    def iddle(self):
        self.memory['a'] += 1
        self.publish(self.memory['a'], 'a')


class SyncSubscriber(Agent):
    def __init__(self, rpp=AgentRPP(), queue=None):
        Agent.__init__(self, rpp, queue)
        self.a = []
    def on_memory(self, memory):
        self.memory = memory
    def on_a(self, data):
        self.a.append(data)


@pytest.fixture(scope='function')
def fast_publisher(request):
    queue = multiprocessing.Queue()
    process = FastPublisher(queue=queue)
    process.start()
    rpp = queue.get()
    def terminate():
        killer = TryREQ(rpp.rep())
        killer.send(Message(mType.DIE))
        killer.recv()
        process.join()
    request.addfinalizer(terminate)
    return rpp


def test_sync(fast_publisher):

    for i in range(10):
        client = SyncSubscriber(AgentRPP())
        client.init_agent()
        client_rpp = client.rpp

        client.sync(fast_publisher, client.on_memory, {'a': client.on_a})
        for i in range(10):
            client.iterate()

        assert client.memory['a'] + 1 == client.a[0]
