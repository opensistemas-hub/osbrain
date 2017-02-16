"""
Core agent classes.
"""
from datetime import datetime
import errno
import inspect
import multiprocessing
import os
import pickle
import json
import signal
import sys
import types
from uuid import uuid4

import dill
import Pyro4
from Pyro4.errors import PyroError
import zmq

from .common import format_exception
from .common import unbound_method
from .common import LogLevel
from .common import repeat
from .address import AgentAddress
from .address import AgentAddressKind
from .address import address_to_host_port
from .proxy import Proxy
from .proxy import NSProxy


def str2bytes(message):
    return message.encode('ascii')


def bytes2str(message):
    return message.decode('ascii')


def check_type(x, check_type):
    if not isinstance(x, check_type):
        msg = 'Expected type `{}`, but got `{}`'.format(check_type, type(x))
        raise TypeError(msg)


def serialize_message(message, serializer):
    """
    Check if a message needs to be serialized and do it if that is the
    case.

    Parameters
    ----------
    message : anything
        The message to serialize.
    serializer : AgentAddressSerializer
        The type of serializer that should be used.

    Returns
    -------
    bytes
        The serialized message, or the same message in case no
        serialization is needed.
    """
    result = None

    if serializer == 'pickle':
        result = pickle.dumps(message, -1)
    if serializer == 'json':
        result = str2bytes(json.dumps(message))
    if serializer == 'raw':
        result = message

    if result is None:
        raise ValueError('Serializer not supported for serialization')

    check_type(result, bytes)

    return result


def deserialize_message(message, serializer):
    """
    Check if a message needs to be deserialized and do it if that is the
    case.

    Parameters
    ----------
    message : bytes
        The serialized message.
    serializer : AgentAddressSerializer
        The type of (de)serializer that should be used.

    Returns
    -------
    anything
        The deserialized message, or the same message in case no
        deserialization is needed.
    """
    check_type(message, bytes)

    result = None

    if serializer == 'pickle':
        result = pickle.loads(message)
    if serializer == 'json':
        result = json.loads(bytes2str(message))
    if serializer == 'raw':
        result = message

    if result is None:
        raise ValueError('Serializer not supported for deserialization')

    return result


def compose_message(serializer, message, topic=''):
    """
    Compose a message and leave it ready to be sent through a socket.

    Parameters
    ----------
    serializer : AgentAddressSerializer
        Serialization for the message part.
    message : anything
        Message to be serialized. The user is the one responsible for passing
        serializable data.
    topic : str
        Topic.

    Returns
    -------
    bytes
        The bytes representation of the final message to be sent.
    """
    assert isinstance(topic, str), 'Topic must be of `str` type!'
    serialized = serialize_message(message=message, serializer=serializer)
    topic = str2bytes(topic)
    if topic and serializer != 'raw':
        separator = b'\x80'
        return topic + separator + serialized
    return topic + serialized


class Agent():
    """
    A base agent class which is to be served by an AgentProcess.

    An AgentProcess runs a Pyro multiplexed server and serves one Agent
    object.

    Parameters
    ----------
    name : str, default is None
        Name of the Agent.
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
        A dictionary in which the key is the address or the alias and the
        value is the actual address.
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
        self._timer = {}
        self.poll_timeout = 1000
        self.keep_alive = True
        self._shutdown_now = False
        self.running = False
        # Kill parent AgentProcess
        self.kill_agent = False
        self._DEBUG = False

        self.context = zmq.Context()
        self.poller = zmq.Poller()

        # A loopback socket where, for example, timers are processed
        self.bind('REP', alias='loopback', addr='loopback',
                  handler=self._handle_loopback, transport='inproc',
                  serializer='pickle')

        # This in-process socket handles safe access to
        # memory from other threads (i.e. when using Pyro proxies).
        self.bind('REP', alias='_loopback_safe', addr='_loopback_safe',
                  handler=self._handle_loopback_safe, transport='inproc',
                  serializer='pickle')

        self.on_init()

    def on_init(self):
        """
        This user-defined method is to be executed after initialization.
        """
        pass

    def _handle_loopback(self, message):
        """
        Handle incoming messages in the loopback socket.
        """
        header, data = message
        if header == 'EXECUTE_METHOD':
            method, args, kwargs = data
            try:
                response = getattr(self, method)(*args, **kwargs)
            except Exception as error:
                message = 'Error executing `%s`! (%s)\n' % (method, error)
                message += '\n> method: %s\n> args: %s\n> kwargs: %s\n' % \
                    (str(method), str(args), str(kwargs))
                message += format_exception()
                aux = type(error)(message)
                self.send('loopback', aux)
                raise
            if not response:
                return True
            return response
        error = 'Unrecognized loopback message: {} {}'.format(header, data)
        self.log_error(error)
        return error

    def _handle_loopback_safe(self, data):
        """
        Handle incoming messages in the _loopback_safe socket.
        """
        method, args, kwargs = dill.loads(data)
        try:
            response = getattr(self, method)(*args, **kwargs)
        except Exception as error:
            message = 'Error executing `%s`! (%s)\n' % (method, error)
            message += '\n> method: %s\n> args: %s\n> kwargs: %s\n' % \
                (str(method), str(args), str(kwargs))
            message += format_exception()
            aux = type(error)(message)
            self.send('_loopback_safe', aux)
            raise
        self.send('_loopback_safe', response)

    def safe_call(self, method, *args, **kwargs):
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
        if not self.running:
            raise RuntimeError(
                'Agent must be running to safely execute methods!')
        data = dill.dumps((method, args, kwargs))
        loopback = self.context.socket(zmq.REQ)
        loopback.connect('inproc://_loopback_safe')
        loopback.send_pyobj(data)
        response = loopback.recv_pyobj()
        loopback.close()
        return response

    def each(self, period, method, *args, alias=None, **kwargs):
        """
        Execute a repeated action with a defined period.

        Parameters
        ----------
        period : float
            Repeat the action execution with a delay of `period` seconds
            between executions.
        method
            Method (action) to be executed by the agent.
        alias : str, default is None
            An alias for the generated timer.
        *args : tuple
            Parameters to pass for the method execution.
        **kwargs : dict
            Named parameters to pass for the method execution.

        Returns
        -------
        str
            The timer alias or identifier.
        """
        if not isinstance(method, str):
            method = self.set_method(method)
        timer = repeat(period, self._loopback,
                       'EXECUTE_METHOD', (method, args, kwargs))
        if not alias:
            alias = uuid4().hex
        self._timer[alias] = timer
        return alias

    def stop_all_timers(self):
        """
        Stop all currently running timers.
        """
        for alias in list(self._timer.keys()):
            self.stop_timer(alias)

    def stop_timer(self, alias):
        """
        Stop a currently running timer.

        Parameters
        ----------
        alias : str
            The alias or identifier of the timer.
        """
        self._timer[alias].stop()
        del self._timer[alias]

    def list_timers(self):
        """
        Returns
        -------
        list (str)
            A list with all the timer aliases currently running.
        """
        return list(self._timer.keys())

    def _loopback(self, header, data=None):
        """
        Send a message to the loopback socket.
        """
        if not self.running:
            raise NotImplementedError()
        loopback = self.context.socket(zmq.REQ)
        loopback.connect('inproc://loopback')
        loopback.send_pyobj((header, data))
        response = loopback.recv_pyobj()
        loopback.close()
        return response

    def ping(self):
        """
        A simple ping method (for testing purposes).
        """
        return 'pong'

    def raise_exception(self):
        """
        Raise an exception (for testing purposes).
        """
        raise RuntimeError('User raised an exception!')

    def stop(self):
        """
        Stop the agent. Agent will stop running.
        """
        self.log_info('Stopping...')
        self.keep_alive = False
        return 'OK'

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
        self.address[address] = address
        if handler is not None:
            self.poller.register(socket, zmq.POLLIN)
            self._set_handler(socket, handler)

    def _set_handler(self, socket, handlers):
        """
        Set the socket handler(s).

        Parameters
        ----------
        socket : zmq.Socket
            Socket to set its handler(s).
        handlers : function(s)
            Handler(s) for the socket. This can be a list or a dictionary too.
        """
        if not isinstance(handlers, (list, dict, tuple)):
            handlers = [handlers]
        self.handler[socket] = self._curated_handlers(handlers)

    def _curated_handlers(self, handlers):
        if isinstance(handlers, (list, tuple)):
            return [self._curate_handler(h) for h in handlers]
        if isinstance(handlers, dict):
            return dict((k, self._curate_handler(v))
                        for k, v in handlers.items())

    def _curate_handler(self, handler):
        if isinstance(handler, str):
            handler = getattr(self, handler)
        function_type = (types.FunctionType, types.BuiltinFunctionType)
        if isinstance(handler, function_type):
            return handler
        method_type = (types.MethodType, types.BuiltinMethodType)
        if isinstance(handler, method_type):
            return unbound_method(handler)
        raise TypeError('Unknow handler type "%s"' % type(handler))

    def registered(self, address):
        return address in self.socket

    def bind(self, kind, alias=None, handler=None, addr=None, transport=None,
             serializer=None):
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
        addr : str, default is None
            The address to bind to.
        transport : str, AgentAddressTransport, default is None
            Transport protocol.

        Returns
        -------
        AgentAddress
            The address where the agent binded to.
        """
        kind = AgentAddressKind(kind)
        assert not kind.requires_handler() or handler is not None, \
            'This socket requires a handler!'
        socket = self.context.socket(kind)
        transport = transport or os.environ.get('OSBRAIN_DEFAULT_TRANSPORT')
        serializer = serializer or os.getenv('OSBRAIN_DEFAULT_SERIALIZER')
        addr = self._bind_socket(socket, addr=addr, transport=transport)
        server_address = AgentAddress(transport, addr, kind, 'server',
                                      serializer)
        self.register(socket, server_address, alias, handler)
        # SUB sockets are a special case
        if kind == 'SUB':
            self.subscribe(server_address, handler)
        return server_address

    def _bind_socket(self, socket, addr=None, transport=None):
        """
        Bind a socket using the corresponding transport and address.

        Parameters
        ----------
        socket : zmq.Socket
            Socket to bind.
        addr : str, default is None
            The address to bind to.
        transport : str, AgentAddressTransport, default is None
            Transport protocol.

        Returns
        -------
        addr : str
            The address where the socket binded to.
        """
        if transport == 'tcp':
            if not addr:
                uri = 'tcp://%s' % self.host
                port = socket.bind_to_random_port(uri)
                addr = self.host + ':' + str(port)
            else:
                socket.bind('tcp://%s' % (addr))
        else:
            if not addr:
                addr = str(uuid4())
            socket.bind('%s://%s' % (transport, addr))
        return addr

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
        if handler is not None:
            raise NotImplementedError('Undefined behavior!')
        self.socket[alias] = self.socket[client_address]
        self.address[alias] = client_address
        return client_address

    def _connect_new(self, client_address, alias=None, handler=None):
        socket = self.context.socket(client_address.kind)
        socket.connect('%s://%s' % (client_address.transport,
                                    client_address.address))
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
            topic = str2bytes(topic)
            self.socket[alias].setsockopt(zmq.SUBSCRIBE, topic)
        # Reset handlers
        self._set_handler(self.socket[alias], handlers)

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

        Returns
        -------
        str
            Name of the registered method in the agent.
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
        return name

    def execute_function(self, function, *args, **kwargs):
        """
        Execute a function passed as parameter.
        """
        return function(args, kwargs)

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
            if error.errno == errno.EINTR:
                return 1
            raise

        if not events:
            # Agent is iddle
            self.iddle()
            return 0

        self._process_events(events)

        return 0

    def _process_events(self, events):
        """
        Process a socket's event.

        Parameters
        ----------
        events : dict
            Events to be processed.
        """
        for socket in events:
            if events[socket] != zmq.POLLIN:
                continue
            self._process_socket_event(socket)

    def _process_socket_event(self, socket):
        """
        Process a socket's event.

        Parameters
        ----------
        socket : zmq.Socket
            Socket that generated the event.
        """
        serialized = socket.recv()
        socket_kind = AgentAddressKind(socket.socket_type)
        if socket_kind == 'SUB':
            self._process_sub_event(socket, serialized)
        else:
            self._process_nonsub_event(socket_kind, socket, serialized)

    def _process_rep_event(self, socket_kind, socket, handler_return,
                           serializer):
        if socket_kind == 'REP' and handler_return is not None:
            handler_return = serialize_message(handler_return, serializer)
            socket.send(handler_return)

    def _process_nonsub_event(self, socket_kind, socket, serialized):
        """
        Process a non-SUB socket's event.

        Parameters
        ----------
        socket_kind : str
            The socket kind (i.e.: REP or PULL).
        socket : zmq.Socket
            Socket that generated the event.
        serialized : bytes
            Data received on the socket.
        """
        serializer = self._get_serialization_from_socket(socket)

        message = deserialize_message(message=serialized,
                                      serializer=serializer)

        handlers = self.handler[socket]
        if not isinstance(handlers, list):
            handlers = [handlers]
        for handler in handlers:
            handler_return = handler(self, message)

        self._process_rep_event(socket_kind, socket, handler_return,
                                serializer)

    def _process_sub_message(self, serializer, message):
        """
        Return the received message in a PUBSUB communication.

        Parameters
        ----------
        message : bytes
            Received message without any treatment. Note that we do not know
            whether there is a topic or not.

        Returns
        -------
        anything
            The content of the message passed.
        """
        separator = b'\x80'

        if serializer == 'pickle':
            if not message.startswith(separator):
                sepp = message.index(separator) + 1
                message = bytes(memoryview(message)[sepp:])

        if serializer == 'json':
            if separator in message:
                sepp = message.index(separator) + 1
                message = bytes(memoryview(message)[sepp:])

        return deserialize_message(message=message, serializer=serializer)

    def _process_sub_event(self, socket, serialized):
        """
        Process a SUB socket's event.

        Parameters
        ----------
        socket : zmq.Socket
            Socket that generated the event.
        serialized : bytes
            Data received on the socket.
        """
        handlers = self.handler[socket]

        serializer = self._get_serialization_from_socket(socket)

        message = self._process_sub_message(serializer, serialized)

        for str_topic in handlers:
            btopic = str2bytes(str_topic)
            if not serialized.startswith(btopic):
                continue
            # Call the handler (with or without the topic)
            handler = handlers[str_topic]
            nparams = len(inspect.signature(handler).parameters)
            if nparams == 2:
                handler(self, message)
            elif nparams == 3:
                handler(self, message, str_topic)

    def _get_serialization_from_socket(self, socket):
        """
        Parameters
        ----------
        socket : zmq.Socket
            Socket which we want to know the type of serialization from.

        Return
        ------
        AgentAddressSerializer
            The serializer type for that socket.
        """
        agent_address = None
        for k, v in self.socket.items():
            if v is socket:
                agent_address = k

        serializer = None
        if isinstance(agent_address, str):
            serializer = self.address[agent_address].serializer
        else:
            serializer = agent_address.serializer

        return serializer

    def send(self, address, message, topic=''):
        """
        Send a message through the specified address.

        Note that replies in a REQREP pattern do not use this function in
        order to be sent.
        """
        serializer = self.address[address].serializer
        message = compose_message(serializer, message, topic)
        self.socket[address].send(message)

    def recv(self, address):
        """
        Receive a message from the specified address.

        This method is only used in REQREP communication patterns.

        Parameters
        ----------
        address :

        Returns
        -------
        anything
            The content received in the address.

        """
        message = self.socket[address].recv()
        serializer = self.address[address].serializer
        return deserialize_message(message=message, serializer=serializer)

    def send_recv(self, address, message):
        """
        This method is only used in REQREP communication patterns.
        """
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
            self.running = False
            msg = 'An exception occured while running! (%s)\n' % error
            msg += format_exception()
            self.log_error(msg)
            raise
        self.running = False
        if self._shutdown_now:
            # Kill the agent
            self.kill()

    def shutdown(self):
        # Stop running timers
        self.stop_all_timers()
        # Stop the running thread
        if self.running:
            self.log_info('Stopping...')
            self.keep_alive = False
            self._shutdown_now = True

    def kill(self):
        self.close_sockets()
        self.kill_agent = True

    def close_sockets(self):
        for address in self.socket:
            if address in ('loopback', '_loopback_safe', 'inproc://loopback',
                           'inproc://_loopback_safe'):
                continue
            self.socket[address].close()

    def ready(self):
        """
        A test method to check the readiness of the agent. Used for testing
        purposes, where timing is very important. Do not remove.
        """
        return 'OK'


class AgentProcess(multiprocessing.Process):
    """
    Agent class. Instances of an Agent are system processes which
    can be run independently.
    """
    def __init__(self, name, nsaddr=None, addr=None, base=Agent):
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
        self.sigint = False

    def run(self):
        # Capture SIGINT
        signal.signal(signal.SIGINT, self.sigint_handler)

        try:
            ns = NSProxy(self.nsaddr)
            self.daemon = Pyro4.Daemon(self.host, self.port)
        except Exception:
            self.queue.put(format_exception())
            return
        self.queue.put('STARTED')

        self.agent = self.base(name=self.name, host=self.host)
        uri = self.daemon.register(self.agent)
        ns.register(self.name, uri)
        ns.release()

        self.daemon.requestLoop(lambda: (not self.shutdown_event.is_set() and
                                         not self.agent.kill_agent))
        self.daemon.unregister(self.agent)

        self._teardown()

    def _teardown(self):
        """
        Remove self from the name server address book, close daemon and die.
        """
        try:
            ns = NSProxy(self.nsaddr, timeout=1.)
            ns.remove(self.name)
        except PyroError:
            if not self.sigint:
                sys.stderr.write(format_exception())
                raise
        finally:
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
        self.sigint = True
        self.kill()


def run_agent(name, nsaddr=None, addr=None, base=Agent):
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
    if not nsaddr:
        nsaddr = os.environ.get('OSBRAIN_NAMESERVER_ADDRESS')
    AgentProcess(name, nsaddr=nsaddr, addr=addr, base=base).start()
    proxy = Proxy(name, nsaddr)
    proxy.run()
    return proxy
