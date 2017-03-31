import os
import Pyro4
Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZERS_ACCEPTED.add('dill')
Pyro4.config.SERIALIZER = 'dill'
Pyro4.config.THREADPOOL_SIZE = 16
Pyro4.config.SERVERTYPE = 'thread'
Pyro4.config.REQUIRE_EXPOSE = False
Pyro4.config.COMMTIMEOUT = 0.
Pyro4.config.DETAILED_TRACEBACK = True

config = {}
config['SAFE'] = os.environ.get('OSBRAIN_DEFAULT_SAFE', 'true') != 'false'
config['SERIALIZER'] = os.environ.get('OSBRAIN_DEFAULT_SERIALIZER', 'pickle')
config['LINGER'] = float(os.environ.get('OSBRAIN_DEFAULT_LINGER', '1'))
config['TRANSPORT'] = os.environ.get('OSBRAIN_DEFAULT_TRANSPORT', 'ipc')


__version__ = '0.4.1'

from .agent import Agent, AgentProcess, run_agent
from .nameserver import run_nameserver
from .proxy import Proxy, NSProxy
from .address import SocketAddress, AgentAddress
from .logging import Logger, run_logger
