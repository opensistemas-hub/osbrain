import Pyro4
Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.THREADPOOL_SIZE = 16
Pyro4.config.SERVERTYPE = 'multiplex'
# TODO: should we set COMMTIMEOUT as well?
Pyro4.config.DETAILED_TRACEBACK = True

__version__ = '0.1.0'

from .core import BaseAgent, Agent, run_agent
from .nameserver import NameServer, random_nameserver, run_nameserver
from .proxy import Proxy, NSProxy
from .address import SocketAddress, AgentAddress
from .logging import Logger, run_logger
