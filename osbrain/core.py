"""
Core agent classes.
"""
import Pyro4
import types
import zmq
import signal
import sys
import multiprocessing
import pprint
import pickle
import errno

from Pyro4.errors import PyroError
from multiprocessing.queues import Queue

from .message import Message
from .message import Types as mType


Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.THREADPOOL_SIZE = 16
Pyro4.config.SERVERTYPE = 'multiplex'
# TODO: should we set COMMTIMEOUT as well?


# TODO:
#   - Consider removing message types?
#       - Perhaps it is fine as long as they are all hidden from the user.
#         (only for basic, low-level messages types!)
#       - Or even better, create a list of "commands" i.e. !PING, !DIE, ...
#         which can be used by the user (create tests for each command).
#   - Message should be hidden from the user: i.e. allow the user to pass
#     messages with 2 parameters (that will automatically be wrapped in a
#     message?
#   - Do not require a message to inherit from Message (it could be anything)?
#       - Perhaps it is fine if we allow a string as Message type (then only
#         the type would be required.
#       - Implement __eq__ to compare a Message to its topic.
#       - Reconsider attribute name `type` to: topic? header? key?...
#   - Tests, tests, tests!
#   - Rethink Agent class and methods (better API)
#   - Implement logging mechanisms (deprecate info(), warn(), ...)
#   - Automatically handle error replies (i.e. log error and skip processing?)
#   - An Agent should only have a REP socket at first. Then any number and
#     type of sockets could be added to it.
#   - Perhaps the init_agent() method makes no sense (could be embedded in
#     __init__().
#   - __getitem__ could select sockets by name (i.e. Agent()['rep0'])

# REVIEW (API examples):
# =============================
# a1 = Agent()
# a2 = Agent()
# =============================
# a1.bind_push(host, port)
# a2.connect_pull(host, port, handler)
# -----------------------------
# address = a1.bind_push(host, port)
# a2.connect_pull(address, handler)
# -----------------------------
# address = Address(host, port)
# a1.bind_push(address)       # If port is changed it is done inside `address`
# a2.connect_pull(address)    # In this case address only contains host + port
# -----------------------------
# address = Address(host, port, kind)
# a1.bind(address)            # If port is changed it is done inside `address`
# a2.connect(address.pair())
# -----------------------------
# a1.bind(kind, host, port)   # May return port
# a2.connect(kind, host, port, handler)
# -----------------------------
# address = Address(host, port, kind, role)
# a1.add(address)            # If port is changed it is done inside `address`
# a2.add(address.pair())
# -----------------------------
# ...


ZMQ_KIND = {
    'REQ': zmq.REQ,
    'REP': zmq.REP,
    'PUSH': zmq.PUSH,
    'PULL': zmq.PULL,
    'PUB': zmq.PUB,
    'SUB': zmq.SUB
}

# TODO: once a class is created to store ZMQ_KIND, a method is to be
#       implemented: .requires_handler(), which returns either True or False
ZMQ_HANDLE = {
    'REQ': False,
    'REP': True,
    'PUSH': False,
    'PULL': True,
    'PUB': False,
    'SUB': True
}

ZMQ_TWIN = {
    'REQ': 'REP',
    'REP': 'REQ',
    'PUSH': 'PULL',
    'PULL': 'PUSH',
    'PUB': 'SUB',
    'SUB': 'PUB'
}


def address_to_host_port(addr):
    # TODO: should we return 0 or None when port is not given?
    if not addr:
        return (None, None)
    # TODO: for now we assume `addr` is a string, but it could be other types
    aux = addr.split(':')
    if len(aux) == 1:
        # TODO: should we return 0 or None when port is not given?
        port = None
    else:
        port = int(aux[-1])
    host = aux[0]
    return (host, port)


class AgentAddress(object):
    """
    Agent address information consisting on the host, port, kind and role.

    Parameters
    ----------
    host : str
        Agent host.
    port : int
        Agent port.
    kind : str
        Agent kind.
    role : str
        Agent role.

    Attributes
    ----------
    host : str
        Agent host.
    port : int
        Agent port.
    kind : str (TODO: create AgentAddressKind class)
        Agent kind.
    role : str (TODO: create AgentAddressRole class)
        Agent role.
    """
    def __init__(self, host, port, kind=None, role=None):
        assert isinstance(host, str), \
            'Incorrect parameter host on AgentAddress; expecting type str.'
        assert isinstance(port, int), \
            'Incorrect parameter port on AgentAddress; expecting type int.'
        assert kind in ZMQ_KIND.keys(), \
            'Incorrect parameter kind "%s" on AgentAddress!' % kind
        assert role in ('server', 'client'), \
            'Incorrect parameter role on AgentAddress!'
        self.host = host
        self.port = port
        self.kind = kind
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
        host = self.host
        port = self.port
        kind = ZMQ_TWIN[self.kind]
        role = 'client' if self.role == 'server' else 'server'
        return AgentAddress(host, port, kind, role)


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
        # TODO: Poller needs at least one registered socket
        #       Implement this properly!
        socket = self.context.socket(zmq.REP)
        host = '127.0.0.1'
        uri = 'tcp://%s' % host
        port = socket.bind_to_random_port(uri)

        self.on_init()

    def on_init(self):
        pass

    def reply(self, message):
        pass

    def log_error(self, message):
        # TODO: implement actual logging methods
        print('ERROR (%s): %s' % (self.name, message))

    def log_info(self, message):
        # TODO: implement actual logging methods
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
        assert kind in ZMQ_KIND, \
            'Wrong socket kind!'
        assert not ZMQ_HANDLE[kind] or handler is not None, \
            'This socket requires a handler!'
        zmq_kind = ZMQ_KIND[kind]
        if not host:
            host = self.host
        try:
            socket = self.context.socket(zmq_kind)
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
        return server_address

    def connect(self, server_address, alias=None, handler=None):
        assert server_address.role == 'server', \
            'Incorrect address! A server address must be provided!'
        client_address = server_address.twin()
        assert not ZMQ_HANDLE[client_address.kind] or handler is not None, \
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
            # TODO: when using `socket(client_address.kind)` and running
            #       (for example) examples/push_pull/, we get a TypeError
            #       (integer is required). However, the line is not displayed.
            #       Perhaps we could improve the traceback display?
            socket = self.context.socket(ZMQ_KIND[client_address.kind])
            socket.connect('tcp://%s:%s' % (client_address.host,
                                            client_address.port))
        except zmq.ZMQError as error:
            self.log_error('Could not connect: %s' % error)
            raise
        self.register(socket, client_address, alias, handler)
        return client_address

    def terminate(self):
        self.log_info('Closing sockets...')
        for address in self.socket:
            self.socket[address].close()
        self.log_info('Terminated!')

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
            # TODO: handle all patterns (i.e.: REQ-REP must reply!)
            message = socket.recv_pyobj()
            self.handler[socket](self, message)

        return 0

    def send(self, address, message):
        self.socket[address].send_pyobj(message)

    def recv(self, address):
        return self.socket[address].recv_pyobj()

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
        self.loop()

        # Terminate agent
        self.terminate()


class Agent(multiprocessing.Process):
    def __init__(self, name, addr=None, nsaddr=None):
        super().__init__()
        self.name = name
        self.daemon = None
        self.host, self.port = address_to_host_port(addr)
        # TODO: pull request?
        if self.port is None:
            self.port = 0
        self.nshost, self.nsport = address_to_host_port(nsaddr)

    def run(self):
        # Capture SIGINT
        signal.signal(signal.SIGINT, self.sigint_handler)

        try:
            ns = Pyro4.locateNS(self.nshost, self.nsport)
        except PyroError as error:
            print(error)
            print('Agent %s is being killed' % self.name)
            return

        # TODO: infer `host` if is `None` and we are connected to `ns_host`
        #       through a LAN.
        ns_host = ns._pyroUri.host

        self.daemon = Pyro4.Daemon(self.host, self.port)
        uri = self.daemon.register(BaseAgent(name=self.name, host=self.host))
        ns.register(self.name, uri)
        ns._pyroRelease()

        print('%s ready!' % self.name)
        self.daemon.requestLoop()

    def sigint_handler(self, signal, frame):
        """
        Handle interruption signals.
        """
        self.daemon.shutdown()


class NameServer(multiprocessing.Process):
    def __init__(self, addr=None):
        super().__init__()
        self.host, self.port = address_to_host_port(addr)

    def run(self):
        # FIXME: for now if `port` is None, it will default to 9090. Perhaps
        #        we could always get a random port (pass 0 as parameter). For
        #        now it does not work (problems with automatic discovering).
        Pyro4.naming.startNSloop(self.host, self.port)


class Proxy(Pyro4.core.Proxy):
    def __init__(self, name, nsaddr=None):
        nshost, nsport = address_to_host_port(nsaddr)
        if nshost is None and nsport is None:
            super().__init__('PYRONAME:%s' % name)
        elif nsport is None:
            super().__init__('PYRONAME:%s@%s' % (name, nshost))
        else:
            super().__init__('PYRONAME:%s@%s:%s' % (name, nshost, nsport))

    def add_method(self, method, name=None):
        self.new_method(method, name)
        if not name:
            name = method.__name__
        if not isinstance(name, str):
            raise ValueError('The new name must be of type `str`!')
        self._pyroMethods.add(name)

    def release(self):
        self._pyroRelease()
