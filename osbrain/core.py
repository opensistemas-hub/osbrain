"""
Core agent classes.
"""
import Pyro4
import types
import zmq
import signal
import sys
import os
import time
import multiprocessing
import pprint
import pickle
import errno

from Pyro4.errors import PyroError
from Pyro4.errors import NamingError
from multiprocessing.queues import Queue


Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.THREADPOOL_SIZE = 16
Pyro4.config.SERVERTYPE = 'multiplex'
# TODO: should we set COMMTIMEOUT as well?


class AgentAddressRole(str):
    """
    Agent's address role class. It can either be 'server' or 'client'.
    """
    def __new__(cls, value):
        if not value in ['server', 'client']:
            raise ValueError('Incorrect value "%s" for `value`!' % value)
        return super().__new__(cls, value)

    def twin(self):
        """
        Returns
        -------
        AgentAddressRole
            The twin role of the current one; `server` would be the twin
            of `client` and viceversa.
        """
        if self == 'server':
            return self.__class__('client')
        if self == 'client':
            return self.__class__('server')


class AgentAddressKind(int):
    """
    Agent's address kind class. It can be any ZMQ type ('REP', 'PUB'...).

    Inherits from `int` to be compatible with ZMQ definitions, however,
    it is represented in its string form. The equivalence can also be
    evaluated against its string form.
    """
    ZMQ_KIND_TWIN = {
        zmq.REQ: zmq.REP,
        zmq.REP: zmq.REQ,
        zmq.PUSH: zmq.PULL,
        zmq.PULL: zmq.PUSH,
        zmq.PUB: zmq.SUB,
        zmq.SUB: zmq.PUB,
    }
    ZMQ_STR_CONVERSION = {
        'REQ': zmq.REQ,
        'REP': zmq.REP,
        'PUSH': zmq.PUSH,
        'PULL': zmq.PULL,
        'PUB': zmq.PUB,
        'SUB': zmq.SUB
    }
    keys = list(ZMQ_STR_CONVERSION.keys())
    for key in keys:
        ZMQ_STR_CONVERSION[ZMQ_STR_CONVERSION[key]] = key

    def __new__(cls, kind):
        if isinstance(kind, str):
            assert kind in cls.ZMQ_STR_CONVERSION, \
                'Incorrect parameter kind `%s`!' % kind
            int_kind = cls.ZMQ_STR_CONVERSION[kind]
        elif isinstance(kind, int):
            assert kind in cls.ZMQ_STR_CONVERSION, \
                'Incorrect parameter kind `%s`!' % kind
            int_kind = kind
        else:
            raise ValueError('Incorrect parameter `kind` of type %s!' %
                    type(kind))
        return super().__new__(cls, int_kind)

    def __eq__(self, other):
        if isinstance(other, int):
            return int(self) == other
        if isinstance(other, str):
            return str(self) == other
        return False

    def __str__(self):
        return self.ZMQ_STR_CONVERSION[self]

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(int(self))

    def requires_handler(self):
        """
        Returns
        -------
        bool
            Whether the Agent's address kind requires a handler or not.
            A socket which processes incoming messages would require a
            handler (i.e. 'REP', 'PULL', 'SUB'...).
        """
        if self.ZMQ_STR_CONVERSION[self] in ('REP', 'PULL', 'SUB'):
            return True
        if self.ZMQ_STR_CONVERSION[self] in ('REQ', 'PUSH', 'PUB'):
            return False

    def twin(self):
        """
        Returns
        -------
        AgentAddressKind
            The twin kind of the current one; `REQ` would be the twin
            of `REP` and viceversa, `PUB` would be the twin of `SUB` and
            viceversa, etc.
        """
        return self.__class__(self.ZMQ_KIND_TWIN[self])


def address_to_host_port(addr=None):
    if addr is None:
        return (None, None)
    if isinstance(addr, SocketAddress):
        return (addr.host, addr.port)
    if not isinstance(addr, str):
        raise ValueError('Only `SocketAddress` and `str` types are supported!')
    aux = addr.split(':')
    if len(aux) == 1:
        port = None
    else:
        port = int(aux[-1])
    host = aux[0]
    return (host, port)


class SocketAddress(object):
    """
    Socket address information consisting on the host and port.

    Parameters
    ----------
    host : str
        Agent host.
    port : int
        Agent port.

    Attributes
    ----------
    host : str
        Agent host.
    port : int
        Agent port.
    """
    def __init__(self, host, port):
        assert isinstance(host, str), \
            'Incorrect parameter host on AgentAddress; expecting type str.'
        assert isinstance(port, int), \
            'Incorrect parameter port on AgentAddress; expecting type int.'
        self.host = host
        self.port = port

    def __repr__(self):
        """
        Return the string representation of the SocketAddress.

        Returns
        -------
        representation : str
        """
        return '%s:%s' % (self.host, self.port)

    def __hash__(self):
        return hash(self.host) ^ hash(self.port)

    def __eq__(self, other):
        if not isinstance(other, SocketAddress):
            return False
        return self.host == other.host and self.port == other.port


class AgentAddress(SocketAddress):
    """
    Agent address information consisting on the host, port, kind and role.

    Parameters
    ----------
    host : str
        Agent host.
    port : int
        Agent port.
    kind : int, str, AgentAddressKind
        Agent kind.
    role : str, AgentAddressRole
        Agent role.

    Attributes
    ----------
    host : str
        Agent host.
    port : int
        Agent port.
    kind : AgentAddressKind
        Agent kind.
    role : AgentAddressRole
        Agent role.
    """
    def __init__(self, host, port, kind=None, role=None):
        super().__init__(host, port)
        if kind is not None:
            self.kind = AgentAddressKind(kind)
        else:
            self.kind = kind
        if role is not None:
            self.role = AgentAddressRole(role)
        else:
            self.role = role

    def __repr__(self):
        """
        Return the string representation of the AgentAddress.

        Returns
        -------
        representation : str
        """
        return '%s:%s (%s %s)' % (self.host, self.port, self.kind, self.role)

    def __hash__(self):
        return hash(self.host) ^ hash(self.port) ^ \
                hash(self.role) ^ hash(self.kind)

    def __eq__(self, other):
        if not isinstance(other, AgentAddress):
            return False
        return self.host == other.host and self.port == other.port and \
                self.role == other.role and self.kind == other.kind

    def twin(self):
        """
        Returns
        -------
        AgentAddress
            The twin address of the current one; while the `host` and `port`
            are kept for the twin, the `kind` and `role` change to their
            corresponding twins, according to the rules defined in the
            respective classes.
        """
        host = self.host
        port = self.port
        kind = self.kind.twin()
        role = self.role.twin()
        return self.__class__(host, port, kind, role)

    def socket_addr(self):
        return SocketAddress(self.host, self.port)


class BaseAgent():
    def __init__(self, name=None, host=None):
        # Set name
        self.name = name

        # The `socket` key is the address or the alias; value is the socket
        self.socket = {}
        # The `address` key is the alias; value is the address
        self.address = {}
        # The `handler` key is the socket
        self.handler = {}
        # Polling timeout
        self.poll_timeout = 1000
        # Keep alive
        self.keep_alive = True
        # Kill parent agent process
        self.kill_agent = False
        # Agent running
        self.running = False
        # Defaut host
        self.host = host
        if not self.host:
            self.host = '127.0.0.1'

        try:
            self.context = zmq.Context()
            self.poller = zmq.Poller()
        except zmq.ZMQError as error:
            self.log_error('Initialization failed: %s' % error)
            raise
        # This in-process socket could, eventually, handle safe access to
        # memory from other threads (i.e. when using Pyro proxies).
        socket = self.context.socket(zmq.REP)
        address = 'inproc://loopback'
        socket.bind(address)
        self.register(socket, address, 'loopback', self.handle_loopback)

        self.on_init()

    def on_init(self):
        pass

    # TODO: __getitem__ could select sockets by name (i.e. Agent()['rep0'])
    def __getitem__(self):
        raise

    def reply(self, message):
        pass

    def handle_loopback(self, agent, message):
        header, data = message
        if header == 'PING':
            return 'PONG'
        if header == 'STOP':
            self.log_info('Stopping...')
            self.keep_alive = False
            return 'OK'
        if header == 'CLOSE':
            self.log_info('Closing sockets...')
            self.close_sockets()
            self.send('loopback', 'OK')

    def loopback(self, header, data=None):
        if not self.running:
            raise NotImplementedError()
        loopback = self.context.socket(zmq.REQ)
        loopback.connect('inproc://loopback')
        loopback.send_pyobj((header, data))
        return loopback.recv_pyobj()

    def ping(self):
        return self.loopback('PING')

    def log_error(self, message):
        if self.registered('log'):
            self.send('log', 'ERROR %s' % message)
        else:
            print('ERROR (%s): %s' % (self.name, message))

    def log_info(self, message):
        if self.registered('log'):
            self.send('log', 'INFO %s' % message)
        else:
            print('INFO (%s): %s' % (self.name, message))

    def get_addr(self, alias):
        return self.address[alias]

    def register(self, socket, address, alias=None, handler=None):
        assert not self.registered(address), \
            'Socket is already registered!'
        if not alias:
            alias = str(address)
        self.socket[alias] = socket
        self.socket[address] = socket
        self.address[alias] = address
        if handler is not None:
            try:
                self.poller.register(socket, zmq.POLLIN)
            except:
                self.error('Error registering socket: %s' % e)
                raise
            self.handler[socket] = handler

    def registered(self, address):
        return address in self.socket

    def bind(self, kind, alias=None, handler=None, host=None, port=None):
        kind = AgentAddressKind(kind)
        assert not kind.requires_handler() or handler is not None, \
            'This socket requires a handler!'
        if not host:
            host = self.host
        try:
            socket = self.context.socket(kind)
            if not port:
                uri = 'tcp://%s' % host
                port = socket.bind_to_random_port(uri)
            else:
                socket.bind('tcp://%s:%s' % (host, port))
        except zmq.ZMQError as error:
            self.log_error('Socket creation failed: %s' % error)
            raise
        server_address = AgentAddress(host, port, kind, 'server')
        self.register(socket, server_address, alias, handler)
        # SUB sockets are a special case
        if kind == 'SUB':
            self.subscribe(server_address, handler)
        return server_address

    def connect(self, server_address, alias=None, handler=None):
        assert server_address.role == 'server', \
            'Incorrect address! A server address must be provided!'
        client_address = server_address.twin()
        assert not client_address.kind.requires_handler() or \
                handler is not None, \
            'This socket requires a handler!'
        if self.registered(client_address):
            self._connect_old(client_address, alias, handler)
        else:
            self._connect_new(client_address, alias, handler)

    def _connect_old(self, client_address, alias=None, handler=None):
        assert handler is None, \
            'Undefined behavior when a new handler is given! (TODO)'
        self.socket[alias] = self.socket[client_address]
        self.address[alias] = client_address
        return client_address

    def _connect_new(self, client_address, alias=None, handler=None):
        try:
            # TODO: when using `socket(str(client_address.kind))` and running
            #       (for example) examples/push_pull/, we get a TypeError
            #       (integer is required). However, the line is not displayed.
            #       Perhaps we could improve the traceback display?
            socket = self.context.socket(client_address.kind)
            socket.connect('tcp://%s:%s' % (client_address.host,
                                            client_address.port))
        except zmq.ZMQError as error:
            self.log_error('Could not connect: %s' % error)
            raise
        self.register(socket, client_address, alias, handler)
        return client_address

    def subscribe(self, alias, handlers):
        """
        TODO
        """
        if not isinstance(handlers, dict):
            handlers = {'': handlers}
        for topic in handlers.keys():
            assert isinstance(topic, str), 'Topic must be of type `str`!'
            topic = self.str2bytes(topic)
            self.socket[alias].setsockopt(zmq.SUBSCRIBE, topic)
        # Reset handlers
        self.handler[self.socket[alias]] = handlers

    def iddle(self):
        """
        This function is to be executed when the agent is iddle.

        After a timeout occurs when the agent's poller receives no data in
        any of its sockets, the agent may execute this function.

        Note
        ----
        The timeout is set by the agent's `poll_timeout` attribute.
        """
        pass

    def set_attr(self, name, value):
        setattr(self, name, value)

    def get_attr(self, name):
        return getattr(self, name)

    def new_method(self, method, name=None):
        method = types.MethodType(method, self)
        if not name:
            name = method.__name__
        setattr(self, name, method)

    def set_loop(self, loop):
        self.loop = types.MethodType(loop, self)

    def execute(self, function, *args, **kwargs):
        return function(args, kwargs)

    def self_execute(self, function, *args, **kwargs):
        if args and kwargs:
            return function(self, args, kwargs)
        if args:
            return function(self, args)
        if kwargs:
            return function(self, kwargs)
        return function(self)

    def loop(self):
        """
        Agent's main loop.

        This loop is executed until the `keep_alive` attribute is False
        or until an error occurs.
        """
        while self.keep_alive:
            if self.iterate():
                break

    def graceful_end(self):
        """
        Agent graceful termination. It ends current loop of work before exiting.
        """
        self.keep_alive = False

    def iterate(self):
        """
        Agent's main iteration.

        This iteration is normally executed inside the main loop.

        The agent is polling all its sockets for input data. It will wait
        for `poll_timeout`; after this period, the method `iddle` will be
        executed before polling again.

        Returns
        -------
        int
            1 if an error occurred during the iteration (we would expect this
            to happen if an interruption occurs during polling).

            0 otherwise.
        """
        try:
            events = dict(self.poller.poll(self.poll_timeout))
        except zmq.ZMQError as error:
            # Raise the exception in case it is not due to SIGINT
            if error.errno != errno.EINTR:
                raise
            else:
                return 1

        if not events:
            # Agent is iddle
            self.iddle()
            return 0

        for socket in events:
            if events[socket] != zmq.POLLIN:
                continue
            serialized = socket.recv()
            socket_kind = AgentAddressKind(socket.socket_type)
            if socket_kind == 'SUB':
                handlers = self.handler[socket]
                for str_topic in handlers:
                    btopic = self.str2bytes(str_topic)
                    if serialized.startswith(btopic):
                        message = pickle.loads(serialized.lstrip(btopic))
                        handlers[str_topic](self, message)
            else:
                message = pickle.loads(serialized)
                handler_return = self.handler[socket](self, message)
            if socket_kind == 'REP':
                if handler_return is not None:
                    socket.send_pyobj(handler_return)

        return 0

    def str2bytes(self, message):
        # TODO: what happens if the topic is non-ASCII?
        return message.encode('ascii')

    def send(self, address, message, topic=''):
        assert isinstance(topic, str), 'Topic must be of `str` type!'
        serialized = pickle.dumps(message, -1)
        topic = self.str2bytes(topic)
        self.socket[address].send(topic + serialized)

    def recv(self, address):
        serialized = self.socket[address].recv()
        deserialized = pickle.loads(serialized)
        return deserialized

    def send_recv(self, address, message):
        self.send(address, message)
        return self.recv(address)

    def ftp_configure(self, addr, user, passwd, path, perm='elr'):
        from pyftpdlib.authorizers import DummyAuthorizer
        from pyftpdlib.handlers import FTPHandler
        from pyftpdlib.servers import FTPServer
        # Create authorizer
        authorizer = DummyAuthorizer()
        authorizer.add_user(user, passwd, path, perm=perm)
        # Create handler
        handler = FTPHandler
        handler.authorizer = authorizer
        # Create server
        host, port = address_to_host_port(addr)
        # TODO: is this necessary? Or would `None` be sufficient?
        if port is None:
            port = 0
        self.ftp_server = FTPServer((host, port), handler)
        return self.ftp_server.socket.getsockname()

    @Pyro4.oneway
    def ftp_run(self):
        # Serve forever
        self.ftp_server.serve_forever()

    def ftp_addr(self):
        return self.ftp_server.socket.getsockname()

    def ftp_retrieve(self, addr, origin, destiny, user, passwd):
        import ftplib
        host, port = addr
        ftp = ftplib.FTP()
        ftp.connect(host, port)
        ftp.login(user, passwd)
        ftp.retrbinary('RETR %s' % origin, open(destiny, 'wb').write)
        ftp.close()
        return destiny

    @Pyro4.oneway
    def run(self):
        """
        Run the agent.
        """
        self.running = True
        self.loop()
        self.running = False

    def stop(self):
        self.loopback('STOP')

    def shutdown(self):
        # Stop the running thread
        self.loopback('STOP')
        while self.running:
            time.sleep(0.1)
        # Kill the agent
        self.kill()

    def kill(self):
        self.context.destroy()
        self.kill_agent = True

    def close_sockets(self):
        for address in self.socket:
            if address in ('loopback', 'inproc://loopback'):
                continue
            self.socket[address].close()

    def test(self):
        """
        A test method to check the readiness of the agent. Used for testing
        purposes, where timing is very important. Do not remove.
        """
        return 'OK'


class Agent(multiprocessing.Process):
    def __init__(self, name, nsaddr=None, addr=None):
        super().__init__()
        self.name = name
        self.daemon = None
        self.host, self.port = address_to_host_port(addr)
        # TODO: pull request?
        if self.port is None:
            self.port = 0
        self.nsaddr = nsaddr
        self.shutdown_event = multiprocessing.Event()
        self.permission_error = multiprocessing.Event()
        self.unknown_error = multiprocessing.Event()
        self.os_error = multiprocessing.Event()
        self.daemon_started = multiprocessing.Event()

    def run(self):
        # Capture SIGINT
        signal.signal(signal.SIGINT, self.sigint_handler)

        try:
            ns = NSProxy(self.nsaddr)
        except PyroError as error:
            print(error)
            print('Agent %s is being killed' % self.name)
            return

        try:
            # TODO: infer `host` if is `None` and we are connected to `ns_host`
            #       through a LAN.
            self.daemon = Pyro4.Daemon(self.host, self.port)
        except PermissionError:
            self.permission_error.set()
            return
        except OSError:
            self.os_error.set()
            return
        except:
            self.unknown_error.set()
            raise
        self.daemon_started.set()

        self.agent = BaseAgent(name=self.name, host=self.host)
        uri = self.daemon.register(self.agent)
        ns.register(self.name, uri)
        ns._pyroRelease()

        print('%s ready!' % self.name)
        self.daemon.requestLoop(lambda: not self.shutdown_event.is_set() and
                                        not self.agent.kill_agent)
        try:
            ns = NSProxy(self.nsaddr)
            ns.remove(self.name)
        except PyroError as error:
            print(error)
            print('Agent %s is being killed' % self.name)
            return
        self.agent._killed = True
        self.daemon.close()

    def start(self):
        super().start()
        # TODO: instead of Event(), use message passing to handle exceptions.
        #       It would be easier to know the exact exception that occurred.
        while not self.daemon_started.is_set() and \
              not self.permission_error.is_set() and \
              not self.os_error.is_set() and \
              not self.unknown_error.is_set():
            time.sleep(0.01)
        if self.unknown_error.is_set():
            raise RuntimeError('Unknown error occured while creating daemon!')
        elif self.os_error.is_set():
            raise OSError('TODO: use message passing to know the exact error')
        elif self.permission_error.is_set():
            self.permission_error.clear()
            raise PermissionError()

    def kill(self):
        self.shutdown_event.set()
        if self.daemon:
            self.daemon.shutdown()

    def sigint_handler(self, signal, frame):
        """
        Handle interruption signals.
        """
        self.kill()


class NameServer(multiprocessing.Process):
    def __init__(self, addr=None):
        super().__init__()
        self.addr = addr
        self.host, self.port = address_to_host_port(addr)
        self.shutdown_event = multiprocessing.Event()
        self.permission_error = multiprocessing.Event()
        self.unknown_error = multiprocessing.Event()
        self.os_error = multiprocessing.Event()
        self.daemon_started = multiprocessing.Event()

    def run(self):
        try:
            self.daemon = Pyro4.naming.NameServerDaemon(self.host, self.port)
        except PermissionError:
            self.permission_error.set()
            return
        except OSError:
            self.os_error.set()
            return
        except:
            self.unknown_error.set()
            raise
        self.daemon_started.set()
        self.uri = self.daemon.uriFor(self.daemon.nameserver)
        self.host = self.uri.host
        self.port = self.uri.port
        self.addr = AgentAddress(self.host, self.port)
        internalUri = self.daemon.uriFor(self.daemon.nameserver, nat=False)
        enableBroadcast=True
        bcserver=None
        hostip=self.daemon.sock.getsockname()[0]
        if hostip.startswith("127."):
            print("Not starting broadcast server for localhost.")
            enableBroadcast=False
        if enableBroadcast:
            # Make sure to pass the internal uri to the broadcast
            # responder. It is almost always useless to let it return
            # the external uri, because external systems won't be able
            # to talk to this thing anyway.
            bcserver=BroadcastServer(internalUri)
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
        # TODO: instead of Event(), use message passing to handle exceptions.
        #       It would be easier to know the exact exception that occurred.
        while not self.daemon_started.is_set() and \
              not self.permission_error.is_set() and \
              not self.os_error.is_set() and \
              not self.unknown_error.is_set():
            time.sleep(0.01)
        if self.unknown_error.is_set():
            raise RuntimeError('Unknown error occured while creating daemon!')
        elif self.os_error.is_set():
            raise OSError('TODO: use message passing to know the exact error')
        elif self.permission_error.is_set():
            self.permission_error.clear()
            raise PermissionError()

    def shutdown_all(self):
        proxy = NSProxy(self.addr)
        agents = proxy.list()
        for agent in agents:
            if agent == 'Pyro.NameServer':
                continue
            agent = Proxy(agent, self.addr)
            agent.shutdown()

    def shutdown(self):
        self.shutdown_all()
        ns = NSProxy(self.addr)
        # Wait for all agents to be shutdown (unregistered)
        while len(ns.list()) > 1:
            time.sleep(0.1)
        self.shutdown_event.set()
        self.terminate()
        self.join()

    def sigint_handler(self, signal, frame):
        """
        Handle interruption signals.
        """
        self.shutdown()


class NSProxy(Pyro4.core.Proxy):
    def __init__(self, nsaddr=None, timeout=3):
        nshost, nsport = address_to_host_port(nsaddr)
        if nsaddr is None:
            nshost = '127.0.0.1'
            nsport = 9090
        # Make sure name server exists
        locate_ns(nsaddr, timeout)
        super().__init__(
                'PYRONAME:Pyro.NameServer@%s:%s' % (nshost, nsport))

    def addr(self):
        return SocketAddress(self._pyroUri.host, self._pyroUri.port)

    def release(self):
        self._pyroRelease()


def locate_ns(nsaddr, timeout=3):
    """
    Locate a name server (ping) to ensure it actually exists.

    Parameters
    ----------
    nsaddr : SocketAddress
        The address where the name server should be up and running.
    timeout : float
        Timeout in seconds before aborting location.

    Returns
    -------
    nsaddr
        The address where the name server was located.

    Raises
    ------
    NamingError
        If the name server could not be located.
    """
    host, port = address_to_host_port(nsaddr)
    if nsaddr is None:
        host = '127.0.0.1'
        port = 9090
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            Pyro4.locateNS(host, port)
            return nsaddr
        except NamingError:
            continue
    raise NamingError('Could not find name server after timeout!')


def run_agent(name, nsaddr=None, addr=None):
    """
    Ease the agent creation process.

    This function will create a new agent, start the process and then run
    its main loop through a proxy.

    Parameters
    ----------
    name : str
        Agent name or alias.
    nsaddr : SocketAddress, default is None
        Name server address.
    addr : SocketAddress, default is None
        New agent address, if it is to be fixed.

    Returns
    -------
    proxy
        A proxy to the new agent.
    """
    Agent(name, nsaddr, addr).start()
    proxy = Proxy(name, nsaddr)
    proxy.run()
    return proxy


class Proxy(Pyro4.core.Proxy):
    def __init__(self, name, nsaddr=None, timeout=3):
        # TODO: perhaps we could add a parameter `start=False` which, in case
        #       is set to `True`, it will automatically start the Agent if it
        #       did not exist.
        nshost, nsport = address_to_host_port(nsaddr)
        # Make sure name server exists
        locate_ns(nsaddr)
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                if nshost is None and nsport is None:
                    super().__init__('PYRONAME:%s' % name)
                elif nsport is None:
                    super().__init__('PYRONAME:%s@%s' % (name, nshost))
                else:
                    super().__init__(
                            'PYRONAME:%s@%s:%s' % (name, nshost, nsport))
            except NamingError:
                continue
            break
        else:
            raise NamingError('Could not find agent after timeout!')
        while time.time() - t0 < timeout:
            try:
                self.test()
            except NamingError:
                continue
            break
        else:
            raise NamingError('Could not test agent!')

    def add_method(self, method, name=None):
        self.new_method(method, name)
        if not name:
            name = method.__name__
        if not isinstance(name, str):
            raise ValueError('The new name must be of type `str`!')
        self._pyroMethods.add(name)

    def release(self):
        self._pyroRelease()
