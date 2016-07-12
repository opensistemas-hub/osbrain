"""
Implementation of name server.
"""
import time
import random
import traceback
import multiprocessing

import Pyro4
from Pyro4.errors import NamingError
from Pyro4.naming import BroadcastServer

from .common import address_to_host_port
from .address import AgentAddress
from .address import SocketAddress
from .proxy import Proxy
from .proxy import NSProxy


class NameServer(multiprocessing.Process):
    """
    Name server class. Instances of a name server are system processes which
    can be run independently.
    """
    def __init__(self, addr=None):
        super().__init__()
        if isinstance(addr, int):
            addr = '127.0.0.1:%s' % addr
        self.addr = addr
        self.host, self.port = address_to_host_port(addr)
        self.shutdown_event = multiprocessing.Event()
        self.uri = None
        self.queue = multiprocessing.Queue()

    def run(self):
        try:
            self.daemon = Pyro4.naming.NameServerDaemon(self.host, self.port)
        except Exception:
            self.queue.put(traceback.format_exc())
            return
        self.queue.put('STARTED')
        self.uri = self.daemon.uriFor(self.daemon.nameserver)
        self.host = self.uri.host
        self.port = self.uri.port
        self.addr = AgentAddress(self.host, self.port)
        internal_uri = self.daemon.uriFor(self.daemon.nameserver, nat=False)
        enable_broadcast = True
        bcserver = None
        hostip = self.daemon.sock.getsockname()[0]
        if hostip.startswith("127."):
            print("Not starting broadcast server for localhost.")
            enable_broadcast = False
        if enable_broadcast:
            # Make sure to pass the internal uri to the broadcast
            # responder. It is almost always useless to let it return
            # the external uri, because external systems won't be able
            # to talk to this thing anyway.
            bcserver = BroadcastServer(internal_uri)
            print("Broadcast server running on %s" % bcserver.locationStr)
            bcserver.runInThread()
        print("NS running on %s (%s)" % (self.daemon.locationStr, hostip))
        print("URI = %s" % self.uri)
        try:
            self.daemon.requestLoop(lambda: not self.shutdown_event.is_set())
        finally:
            self.daemon.close()
            if bcserver is not None:
                bcserver.close()
        print("NS shut down.")

    def start(self):
        super().start()
        status = self.queue.get()
        if status == 'STARTED':
            return
        raise RuntimeError('An error occured while creating the daemon!' +
                           '\n===============\n'.join(['', status, '']))

    def agents(self):
        """
        List agents registered in the name server.
        """
        proxy = NSProxy(self.addr)
        agents = proxy.list()
        proxy.release()
        return [name for name in agents if name != 'Pyro.NameServer']

    def shutdown_all(self):
        """
        Shutdown all agents registered in the name server.
        """
        for agent in self.agents():
            agent = Proxy(agent, self.addr)
            agent.shutdown()

    def shutdown(self):
        """
        Shutdown the name server. All agents will be shutdown as well.
        """
        self.shutdown_all()
        nameserver = NSProxy(self.addr)
        # Wait for all agents to be shutdown (unregistered)
        while len(nameserver.list()) > 1:
            time.sleep(0.1)
        self.shutdown_event.set()
        self.terminate()
        self.join()

    def sigint_handler(self, signal, frame):
        """
        Handle interruption signals.
        """
        self.shutdown()


def random_nameserver():
    """
    Start a random name server.

    Returns
    -------
    SocketAddress
        The name server address.
    """
    while True:
        try:
            # Bind to random port
            host = '127.0.0.1'
            port = random.randrange(10000, 20000)
            addr = SocketAddress(host, port)
            nameserver = NameServer(addr)
            nameserver.start()
            return addr
        except NamingError:
            continue
        except PermissionError:
            continue
        except:
            raise


def run_nameserver(addr=None):
    """
    Ease the name server creation process.

    This function will create a new nameserver, start the process and then run
    its main loop through a proxy.

    Parameters
    ----------
    addr : SocketAddress, default is None
        Name server address.

    Returns
    -------
    proxy
        A proxy to the name server.
    """
    if not addr:
        addr = random_nameserver()
    else:
        NameServer(addr).start()
    return NSProxy(addr)
