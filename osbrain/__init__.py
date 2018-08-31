import os
import sys
from pathlib import Path

# While Python 3.4 is supported...
if sys.version_info < (3, 5):
    def mkdir(directory, **kwargs):
        directory = str(directory)
        os.makedirs(directory, exist_ok=kwargs['exist_ok'])

    from os.path import expanduser
    Path.home = lambda: Path(expanduser('~'))
    Path.mkdir = lambda directory, **kwargs: mkdir(directory, **kwargs)

import Pyro4
Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZERS_ACCEPTED.add('cloudpickle')
Pyro4.config.SERIALIZERS_ACCEPTED.add('dill')
Pyro4.config.SERIALIZER = 'cloudpickle'
Pyro4.config.THREADPOOL_SIZE = 16
Pyro4.config.SERVERTYPE = 'thread'
Pyro4.config.REQUIRE_EXPOSE = False
Pyro4.config.COMMTIMEOUT = 0.
Pyro4.config.DETAILED_TRACEBACK = True

config = {}
config['SAFE'] = os.environ.get('OSBRAIN_DEFAULT_SAFE', 'true') != 'false'
config['SERIALIZER'] = os.environ.get('OSBRAIN_DEFAULT_SERIALIZER', 'pickle')
config['LINGER'] = float(os.environ.get('OSBRAIN_DEFAULT_LINGER', '1'))
# Set IPC by default only for POSIX systems
if os.name != 'posix':
    config['TRANSPORT'] = os.environ.get('OSBRAIN_DEFAULT_TRANSPORT', 'tcp')
    config['IPC_DIR'] = Path('')
else:
    config['TRANSPORT'] = os.environ.get('OSBRAIN_DEFAULT_TRANSPORT', 'ipc')
    # Set storage folder for IPC socket files
    config['IPC_DIR'] = \
        Path(os.environ.get('XDG_RUNTIME_DIR', Path.home())) / '.osbrain_ipc'
    config['IPC_DIR'].mkdir(exist_ok=True, parents=True)


__version__ = '0.6.3'

from .agent import Agent, AgentProcess, run_agent
from .nameserver import NameServer, run_nameserver
from .proxy import Proxy, NSProxy
from .address import SocketAddress, AgentAddress
from .logging import Logger, run_logger
