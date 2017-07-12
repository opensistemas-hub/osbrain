"""
Implementation of name server.
"""
import os
import sys
import time
import random
import multiprocessing

import Pyro4
from Pyro4.naming import BroadcastServer

from .common import format_exception
from .address import address_to_host_port
from .address import SocketAddress
from .proxy import Proxy
from .proxy import NSProxy


@Pyro4.expose
class NameServer(Pyro4.naming.NameServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ping(self):
        """
        A simple test method to check if the name server is running correctly.
        """
        return 'pong'

    def agents(self):
        """
        List agents registered in the name server.
        """
        agents = self.list()
        return [name for name in agents if name != 'Pyro.NameServer']

    def async_shutdown_agents(self, nsaddr):
        """
        Shutdown all agents registered in the name server.
        """
        for name in self.agents():
            agent = Proxy(name, nsaddr=nsaddr)
            if agent.get_attr('running'):
                agent.after(0, 'shutdown')
            else:
                agent.oneway.kill()
            agent._pyroRelease()

    def daemon_shutdown(self):
        """
        Shutdown the name server daemon.
        """
        self._pyroDaemon.shutdown()


class NameServerProcess(multiprocessing.Process):
    """
    Name server class. Instances of a name server are system processes which
    can be run independently.
    """
    def __init__(self, addr=None, base=NameServer):
        super().__init__()
        self._daemon = None
        self.base = base
        if isinstance(addr, int):
            addr = '127.0.0.1:%s' % addr
        self.addr = addr
        self.host, self.port = address_to_host_port(addr)
        self.shutdown_event = multiprocessing.Event()
        self.uri = None
        self.queue = multiprocessing.Queue()

    def run(self):
        # Capture SIGINT

        try:
            Pyro4.naming.NameServer = self.base
            self._daemon = Pyro4.naming.NameServerDaemon(self.host, self.port)
        except Exception:
            self.queue.put(format_exception())
            return
        self.queue.put('STARTED')
        self.uri = self._daemon.uriFor(self._daemon.nameserver)
        self.host = self.uri.host
        self.port = self.uri.port
        self.addr = SocketAddress(self.host, self.port)
        internal_uri = self._daemon.uriFor(self._daemon.nameserver, nat=False)
        bcserver = None
        hostip = self._daemon.sock.getsockname()[0]
        # Start broadcast responder
        bcserver = BroadcastServer(internal_uri)
        sys.stdout.write(
            "Broadcast server running on %s\n" % bcserver.locationStr)
        sys.stdout.flush()
        bcserver.runInThread()
        sys.stdout.write(
            "NS running on %s (%s)\n" % (self._daemon.locationStr, hostip))
        sys.stdout.write("URI = %s\n" % self.uri)
        sys.stdout.flush()
        try:
            self._daemon.requestLoop(lambda: not self.shutdown_event.is_set())
        finally:
            self._daemon.close()
            if bcserver is not None:
                bcserver.close()
        sys.stdout.write("NS shut down.\n")
        sys.stdout.flush()

    def start(self):
        os.environ['OSBRAIN_NAMESERVER_ADDRESS'] = str(self.addr)
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
            with Proxy(agent, self.addr) as agent:
                agent.after(0, 'shutdown')

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


def random_nameserver_process(host='127.0.0.1', port_start=10000,
                              port_stop=20000, timeout=3., base=NameServer):
    """
    Start a random NameServerProcess.

    Parameters
    ----------
    host : str, default is '127.0.0.1'
        Host address where the name server will bind to.
    port_start : int
        Lowest port number allowed.
    port_stop : int
        Highest port number allowed.

    Returns
    -------
    NameServerProcess
        The name server process started.
    """
    t0 = time.time()
    exception = TimeoutError('Name server starting timed out!')
    while True:
        try:
            # Bind to random port
            port = random.randrange(port_start, port_stop + 1)
            addr = SocketAddress(host, port)
            nameserver = NameServerProcess(addr, base=base)
            nameserver.start()
            return nameserver
        except RuntimeError as error:
            exception = error
        if time.time() - t0 > timeout:
            raise exception


def run_nameserver(addr=None, base=NameServer):
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
        addr = random_nameserver_process(base=base).addr
    else:
        NameServerProcess(addr, base=base).start()
    return NSProxy(addr)
