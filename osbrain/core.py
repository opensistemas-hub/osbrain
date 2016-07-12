"""
Core agent classes.
"""
import types
import signal
import sys
import time
import inspect
import traceback
import multiprocessing
from datetime import datetime

import pickle
import errno
import zmq
import Pyro4
from Pyro4.errors import PyroError

from .common import address_to_host_port
from .common import unbound_method
from .common import LogLevel
from .address import AgentAddress
from .address import AgentAddressKind
from .proxy import Proxy
from .proxy import NSProxy


class BaseAgent():
    """
    A base agent class which is to be served by the Agent process.

    An agent process runs a Pyro multiplexed server and serves one BaseAgent
    object.

    Parameters
    ----------
    name : str, default is None
        Name of the BaseAgent.
    host : str, default is None
        Host address where the agent will bind to. When not set, `'127.0.0.1'`
        (localhost) is used.

    Attributes
    ----------
    name : str
        Name of the agent.
    host : str
        Host address where the agent is binding to.
    socket : dict
        A dictionary in which the key is the address or the alias and the
        value is the actual socket.
    adddress : dict
        A dictionary in which the key is the alias and the value is the
        actual address.
    handler : dict
        A dictionary in which the key is the socket and the values are the
        handlers for each socket.
    poll_timeout : int
        Polling timeout, in milliseconds. After this timeout, if no message
        is received, the agent executes de `iddle()` method before going back
        to polling.
    keep_alive : bool
        When set to `True`, the agent will continue executing the main loop.
    running : bool
        Set to `True` if the agent is running (executing the main loop).
    """
    def __init__(self, name=None, host=None):
        self.name = name
        self.host = host
        if not self.host:
            self.host = '127.0.0.1'
        self.socket = {}
        self.address = {}
        self.handler = {}
        self.poll_timeout = 1000
        self.keep_alive = True
        self.running = False
        # Kill parent agent process
        self.kill_agent = False
        self._DEBUG = False

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
        """
        This user-defined method is to be executed after initialization.
        """
        pass

    def handle_loopback(self, message):
        """
        Handle incoming messages in the loopback socket.
        """
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
            return 'OK'
        if header == 'EXECUTE_METHOD':
            method, args, kwargs = data
            try:
                response = getattr(self, method)(*args, **kwargs)
            except Exception as error:
                message = 'Error executing `%s`! (%s)\n' % (method, error)
                message += traceback.format_exc()
                self.send('loopback', message)
                raise
            if not response:
                return True
            return response
        self.log_error('Unrecognized message: %s %s' % (header, data))

    def safe(self, method, *args, **kwargs):
        """
        A safe call to a method.

        A safe call is simply sent to be executed by the main thread.

        Parameters
        ----------
        method : str
            Method name to be executed by the main thread.
        *args : arguments
            Method arguments.
        *kwargs : keyword arguments
            Method keyword arguments.
        """
        return self.loopback('EXECUTE_METHOD', (method, args, kwargs))

    def loopback(self, header, data=None):
        """
        Send a message to the loopback socket.
        """
        if not self.running:
            raise NotImplementedError()
        loopback = self.context.socket(zmq.REQ)
        loopback.connect('inproc://loopback')
        loopback.send_pyobj((header, data))
        return loopback.recv_pyobj()

    def safe_ping(self):
        """
        A simple loopback ping for testing purposes.
        """
        return self.loopback('PING')

    def ping(self):
        """
        A simple ping method testing purposes.
        """
        return 'PONG'

    def raise_exception(self):
        """
        Raise an exception (for testing purposes).
        """
        raise RuntimeError('User raised an exception!')

    def stop(self):
        """
        Stop the agent. Agent will stop running.
        """
        return self.loopback('STOP')

    def set_logger(self, logger, alias='_logger'):
        """
        Connect the agent to a logger and start logging messages to it.
        """
        if isinstance(logger, Proxy):
            logger = logger.addr('sub')
        if not isinstance(logger, AgentAddress):
            raise ValueError('An AgentAddress must be provided for logging!')
        self.connect(logger, alias=alias)

    def _log_message(self, level, message, logger='_logger'):
        """
        Log a message.

        Parameters
        ----------
        level : LogLevel
            Logging severity level: INFO, WARNING, ERROR, DEBUG.
        message : str
            Message to log.
        logger : str
            Alias of the logger.
        """
        level = LogLevel(level)
        # Ignore DEBUG logs if not `self._DEBUG`
        if level == 'DEBUG' and not self._DEBUG:
            return
        message = '[%s] (%s): %s' % (datetime.utcnow(), self.name, message)
        if self.registered(logger):
            logger_kind = AgentAddressKind(self.socket[logger].socket_type)
            assert logger_kind == 'PUB', \
                'Logger must use publisher-subscriber pattern!'
            self.send(logger, message, topic=level)
        elif level in ('INFO', 'DEBUG'):
            sys.stdout.write('%s %s\n' % (level, message))
            sys.stdout.flush()
        # When logging an error, always write to stderr
        if level == 'ERROR':
            sys.stderr.write('ERROR %s\n' % message)
            sys.stderr.flush()
        # When logging a warning, always write to stdout
        elif level == 'WARNING':
            sys.stdout.write('WARNING %s\n' % message)
            sys.stdout.flush()

    def log_error(self, message, logger='_logger'):
        """
        Log an error message.

        Parameters
        ----------
        message : str
            Message to log.
        logger : str
            Alias of the logger.
        """
        self._log_message('ERROR', message, logger)

    def log_warning(self, message, logger='_logger'):
        """
        Log a warning message.

        Parameters
        ----------
        message : str
            Message to log.
        logger : str
            Alias of the logger.
        """
        self._log_message('WARNING', message, logger)

    def log_info(self, message, logger='_logger'):
        """
        Log an info message.

        Parameters
        ----------
        message : str
            Message to log.
        logger : str
            Alias of the logger.
        """
        self._log_message('INFO', message, logger)

    def log_debug(self, message, logger='_logger'):
        """
        Log a debug message.

        Parameters
        ----------
        message : str
            Message to log.
        logger : str
            Alias of the logger.
        """
        # Ignore DEBUG logs if not `self._DEBUG`
        if not self._DEBUG:
            return
        self._log_message('DEBUG', message, logger)

    def addr(self, alias):
        """
        Parameters
        ----------
        alias : str
            Alias of the socket whose address is to be retreived.

        Returns
        -------
        AgentAddress
            Address of the agent socket associated with the alias.
        """
        return self.address[alias]

    def register(self, socket, address, alias=None, handler=None):
        assert not self.registered(address), \
            'Socket is already registered!'
        if not alias:
            alias = address
        self.socket[alias] = socket
        self.socket[address] = socket
        self.address[alias] = address
        if handler is not None:
            try:
                self.poller.register(socket, zmq.POLLIN)
            except zmq.ZMQError as error:
                self.log_error('Error registering socket: %s' % error)
                raise
            self.set_handler(socket, handler)

    def set_handler(self, socket, handler):
        if isinstance(handler, types.FunctionType):
            self.handler[socket] = handler
            return
        if isinstance(handler, types.MethodType):
            self.handler[socket] = unbound_method(handler)
            return
        if isinstance(handler, list):
            handlers = []
            for h in handler:
                if isinstance(h, types.FunctionType):
                    handlers.append(h)
                elif isinstance(h, types.MethodType):
                    handlers.append(unbound_method(h))
            self.handler[socket] = handlers
            return
        if isinstance(handler, dict):
            handlers = {}
            for key in handler:
                if isinstance(handler[key], types.FunctionType):
                    handlers[key] = handler[key]
                elif isinstance(handler[key], types.MethodType):
                    handlers[key] = unbound_method(handler[key])
            self.handler[socket] = handlers
            return
        # TODO: allow `str` (method name)
        raise NotImplementedError('Only functions/methods are allowed!')

    def registered(self, address):
        return address in self.socket

    def bind(self, kind, alias=None, handler=None, host=None, port=None):
        """
        Bind to an agent address.

        Parameters
        ----------
        kind : str, AgentAddressKind
            The agent address kind: PUB, REQ...
        alias : str, default is None
            Optional alias for the socket.
        handler, default is None
            If the socket receives input messages, the handler/s is/are to
            be set with this parameter.
        host : str, default is None
            The host to bind to, when not given `self.host` is taken as
            default.
        port : int, default is None
            An optional port number. If not set, a random port is used for
            binding.
        """
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
        """
        Connect to a server agent address.

        Parameters
        ----------
        server_address : AgentAddress
            Agent address to connect to.
        alias : str, default is None
            Optional alias for the new address.
        handler, default is None
            If the new socket receives input messages, the handler/s is/are to
            be set with this parameter.
        """
        assert server_address.role == 'server', \
            'Incorrect address! A server address must be provided!'
        client_address = server_address.twin()
        assert not client_address.kind.requires_handler() or \
            handler is not None, 'This socket requires a handler!'
        if self.registered(client_address):
            self._connect_old(client_address, alias, handler)
        else:
            self._connect_new(client_address, alias, handler)
        if client_address.kind == 'SUB':
            if not alias:
                alias = client_address
            self.subscribe(alias, handler)

    def _connect_old(self, client_address, alias=None, handler=None):
        assert handler is None, \
            'Undefined behavior when a new handler is given! (TODO)'
        self.socket[alias] = self.socket[client_address]
        self.address[alias] = client_address
        return client_address

    def _connect_new(self, client_address, alias=None, handler=None):
        try:
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
        Subscribe the agent to another agent.

        Parameters
        ----------
        alias : str
            Alias of the new subscriber socket.
        handlers : dict
            A dictionary in which the keys represent the different topics
            and the values the actual handlers. If ,instead of a dictionary,
            a single handler is given, it will be used to subscribe the agent
            to any topic.
        """
        if not isinstance(handlers, dict):
            handlers = {'': handlers}
        for topic in handlers.keys():
            assert isinstance(topic, str), 'Topic must be of type `str`!'
            topic = self.str2bytes(topic)
            self.socket[alias].setsockopt(zmq.SUBSCRIBE, topic)
        # Reset handlers
        self.set_handler(self.socket[alias], handlers)

    def timer(self, timeout, function):
        raise NotImplementedError('Timers are not implemented yet. (TODO)')

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

    def set_attr(self, **kwargs):
        """
        Set object attributes.

        Parameters
        ----------
        kwargs : [name, value]
            Keyword arguments will be used to set the object attributes.
        """
        for name, value in kwargs.items():
            setattr(self, name, value)
            self.log_info('SET self.%s = %s' % (name, value))

    def get_attr(self, name):
        return getattr(self, name)

    # TODO: merge set_method() and set_attr() into set()? or rather make
    #       the proxy able to set attributes and methods automatically with
    #       `proxy.x = y`?
    def set_method(self, *args, **kwargs):
        """
        Set object methods.

        Parameters
        ----------
        args : [function]
            New methods will be created for each function, taking the same
            name as the original function.
        kwargs : [name, function]
            New methods will be created for each function, taking the name
            specified by the parameter.
        """
        for function in args:
            method = types.MethodType(function, self)
            name = method.__name__
            setattr(self, name, method)
            self.log_info('SET self.%s() = %s' % (name, function))
        for name, function in kwargs.items():
            method = types.MethodType(function, self)
            setattr(self, name, method)
            self.log_info('SET self.%s() = %s' % (name, function))

    # TODO: remove/deprecate. If an Agent is to be active, then loopback could
    #       be used to send execution orders. E.g.: each second, send function
    #       over loopback and let it be executed by the main thread.
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
                sepp = serialized.index(b'\x80')
                data = serialized[sepp:]
                try:
                    message = pickle.loads(data)
                except ValueError:
                    error = 'Could not load pickle stream! %s' % data
                    self.log_error(error)
                    continue
                for str_topic in handlers:
                    btopic = self.str2bytes(str_topic)
                    if not serialized.startswith(btopic):
                        continue
                    # Call the handler (with or without the topic)
                    handler = handlers[str_topic]
                    nparams = len(inspect.signature(handler).parameters)
                    if nparams == 2:
                        handler(self, message)
                    elif nparams == 3:
                        handler(self, message, str_topic)
            else:
                message = pickle.loads(serialized)
                handlers = self.handler[socket]
                if not isinstance(handlers, list):
                    handlers = [handlers]
                # TODO: test (allow multiple handlers, which get executed in
                #       order)
                for handler in handlers:
                    handler_return = handler(self, message)
            if socket_kind == 'REP':
                if handler_return is not None:
                    socket.send_pyobj(handler_return)

        return 0

    def str2bytes(self, message):
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

    @Pyro4.oneway
    def run(self):
        """
        Run the agent.
        """
        self.running = True
        try:
            self.loop()
        except Exception as error:
            msg = 'An exception occured while running! (%s)\n' % error
            msg += traceback.format_exc()
            self.log_error(msg)
            self.running = False
            raise
        self.running = False

    def shutdown(self):
        # Stop the running thread
        if self.running:
            self.loopback('STOP')
        while self.running:
            time.sleep(0.1)
        # Kill the agent
        self.kill()

    def kill(self):
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
    """
    Agent class. Instances of an Agent are system processes which
    can be run independently.
    """
    def __init__(self, name, nsaddr=None, addr=None, base=BaseAgent):
        super().__init__()
        self.name = name
        self.daemon = None
        self.host, self.port = address_to_host_port(addr)
        if self.port is None:
            self.port = 0
        self.nsaddr = nsaddr
        self.base = base
        self.shutdown_event = multiprocessing.Event()
        self.queue = multiprocessing.Queue()

    def run(self):
        # Capture SIGINT
        signal.signal(signal.SIGINT, self.sigint_handler)

        try:
            ns = NSProxy(self.nsaddr)
            self.daemon = Pyro4.Daemon(self.host, self.port)
        except Exception:
            self.queue.put(traceback.format_exc())
            return
        self.queue.put('STARTED')

        self.agent = self.base(name=self.name, host=self.host)
        uri = self.daemon.register(self.agent)
        ns.register(self.name, uri)
        ns.release()

        self.daemon.requestLoop(lambda: (not self.shutdown_event.is_set() and
                                         not self.agent.kill_agent))
        self.daemon.unregister(self.agent)

        try:
            ns = NSProxy(self.nsaddr)
            ns.remove(self.name)
        except PyroError:
            sys.stderr.write(traceback.format_exc())
            pass

        self.agent._killed = True
        self.daemon.close()

    def start(self):
        super().start()
        status = self.queue.get()
        if status == 'STARTED':
            return
        raise RuntimeError('An error occured while creating the daemon!' +
                           '\n===============\n'.join(['', status, '']))

    def kill(self):
        self.shutdown_event.set()
        if self.daemon:
            self.daemon.shutdown()

    def sigint_handler(self, signal, frame):
        """
        Handle interruption signals.
        """
        self.kill()


def run_agent(name, nsaddr=None, addr=None, base=BaseAgent):
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
    Agent(name, nsaddr=nsaddr, addr=addr, base=base).start()
    proxy = Proxy(name, nsaddr)
    proxy.run()
    return proxy
