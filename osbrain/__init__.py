import Pyro4
Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZERS_ACCEPTED.add('dill')
Pyro4.config.SERIALIZER = 'dill'
Pyro4.config.THREADPOOL_SIZE = 16
Pyro4.config.SERVERTYPE = 'multiplex'
Pyro4.config.REQUIRE_EXPOSE = False
# TODO: should we set COMMTIMEOUT as well?
Pyro4.config.DETAILED_TRACEBACK = True

__version__ = '0.3.0'

from .core import Agent, AgentProcess, run_agent
from .nameserver import random_nameserver, run_nameserver
from .proxy import Proxy, NSProxy
from .address import SocketAddress, AgentAddress
from .logging import Logger, run_logger
