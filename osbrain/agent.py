"""
Core agent classes.
"""
import contextlib
from datetime import datetime
import errno
import inspect
import multiprocessing
import os
import pickle
import json
import signal
import sys
import time
import types
from typing import Any
from typing import Dict
from typing import Union

import cloudpickle
import dill
import Pyro4
from Pyro4.errors import PyroError
import zmq

from . import config
from .common import format_exception
from .common import format_method_exception
from .common import topic_to_bytes
from .common import topics_to_bytes
from .common import unbound_method
from .common import validate_handler
from .common import LogLevel
from .common import repeat
from .common import after
from .common import get_linger
from .common import unique_identifier
from .address import AgentAddress
from .address import AgentAddressKind
from .address import AgentAddressSerializer
from .address import AgentChannel
from .address import address_to_host_port
from .address import guess_kind
from .proxy import Proxy
from .proxy import NSProxy


TOPIC_SEPARATOR = b'\x80'

_serialize_calls = {
    'pickle': lambda message: pickle.dumps(message, -1),
    'cloudpickle': lambda message: cloudpickle.dumps(message, -1),
    'dill': lambda message: dill.dumps(message, -1),
    'json': lambda message: json.dumps(message).encode(),
    'raw': lambda message: message,
}

_deserialize_calls = {
    'pickle': lambda message: pickle.loads(message),
    'cloudpickle': lambda message: cloudpickle.loads(message),
    'dill': lambda message: dill.loads(message),
    'json': lambda message: json.loads(bytes(message).decode()),
    'raw': lambda message: message,
}


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
    try:
        return _serialize_calls[serializer](message)
    except KeyError:
        raise ValueError('"%s" not supported for serialization' % serializer)


def deserialize_message(message, serializer):
    """
    Check if a message needs to be deserialized and do it if that is the
    case.

    Parameters
    ----------
    message : bytes, memoryview
        The serialized message.
    serializer : AgentAddressSerializer
        The type of (de)serializer that should be used.

    Returns
    -------
    anything
        The deserialized message, or the same message in case no
        deserialization is needed.
    """
    try:
        return _deserialize_calls[serializer](message)
    except KeyError:
        raise ValueError('"%s" not supported for deserialization' % serializer)


def compose_message(message: bytes, topic: bytes,
                    serializer: AgentAddressSerializer) -> bytes:
    """
    Compose a message and leave it ready to be sent through a socket.

    This is used in PUB-SUB patterns to combine the topic and the message
    in a single bytes buffer.

    Parameters
    ----------
    message
        Message to be composed.
    topic
        Topic to combine the message with.
    serializer
        Serialization for the message part.

    Returns
    -------
        The bytes representation of the final message to be sent.
    """
    if serializer.requires_separator:
        return topic + TOPIC_SEPARATOR + message
    return topic + message


def execute_code_after_yield(generator):
    """
    Some responses are dispatched with yield (generator handler). In those
    cases we still want to execute the remaining code in the generator, and
    also make sure it does not yield any more.

    Parameter
    ---------
    generator
        The handler that already yielded one result and is not expected to
        yield again.

    Raises
    ------
    ValueError
        If the generator yielded once more, which is unexpected.
    """
    try:
        next(generator)
    except StopIteration:
        pass
    else:
        raise ValueError('Reply handler yielded more than once!')


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
    transport : str, AgentAddressTransport, default is None
        Transport protocol.
    attributes : dict, default is None
        A dictionary that defines initial attributes for the agent.

    Attributes
    ----------
    name : str
        Name of the agent.

    _host : str
        Host address where the agent is binding to.
    _uuid : bytes
        Globally unique identifier for the agent.
    _running : bool
        Set to `True` if the agent is running (executing the main loop).
    _serializer : str
        Default agent serialization format.
    _transport : str, AgentAddressTransport, default is None
        Default agent transport protocol.
    _socket : dict
        A dictionary in which the key is the address or the alias and the
        value is the actual socket.
    _address : dict
        A dictionary in which the key is the address or the alias and the
        value is the actual address.
    _handler : dict
        A dictionary in which the key is the socket and the values are the
        handlers for each socket.
    _context : zmq.Context
        ZMQ context to create ZMQ socket objects.
    _poller : zmq.Poller
        ZMQ poller to wait for incoming data from sockets.
    _poll_timeout : int
        Polling timeout, in milliseconds. After this timeout, if no message
        is received, the agent executes de `idle()` method before going back
        to polling.
    _keep_alive : bool
        When set to `True`, the agent will continue executing the main loop.
    _async_req_uuid : dict
        Stores the UUIDs of the asynchronous request sockets (used in
        communication channels).
    _async_req_handler : dict
        Stores the handler for every asynchronous request sockets (used in
        communication channels).
    _die_now : bool
        During shutdown, this attribute is set for the agent to die.
    _DEBUG : bool
        Whether to print debug level messages.
    _pending_requests : dict
        Stores pending (waiting for reply) asynchronous requests. The
        asynchronous request UUID is used as key and its handler as the value.
    _timer : dict
        Stores all the current active timers, using their aliases as keys.
    """
    def __init__(self, name='', host=None, serializer=None, transport=None,
                 attributes=None):
        self._uuid = unique_identifier()
        self.name = name
        if not self.name:
            self.name = self._uuid.decode()

        self._host = host
        if not self._host:
            self._host = '127.0.0.1'
        self._serializer = serializer
        self._transport = transport
        self._socket = {}
        self._address = {}
        self._handler = {}
        self._async_req_uuid = {}
        self._async_req_handler = {}
        self._pending_requests = {}
        self._timer = {}
        self._poll_timeout = 1000
        self._keep_alive = True
        self._die_now = False
        self._running = False
        self._DEBUG = False

        self._context = zmq.Context()
        self._poller = zmq.Poller()

        self._set_attributes(attributes)
        self.on_init()

    def _set_attributes(self, attributes):
        if not attributes:
            return

        for key, value in attributes.items():
            if hasattr(self, key):
                raise KeyError('Agent already has "%s" attribute!' % key)
            setattr(self, key, value)

    def on_init(self):
        """
        This user-defined method is to be executed after initialization.
        """
        pass

    def before_loop(self):
        """
        This user-defined method is to be executed right before the main loop.
        """
        pass

    def _handle_loopback(self, message):
        """
        Handle incoming messages in the loopback socket.
        """
        header, data = cloudpickle.loads(message)
        if header == 'EXECUTE_METHOD':
            method, args, kwargs = data
            try:
                response = getattr(self, method)(*args, **kwargs)
            except Exception as error:
                yield format_method_exception(error, method, args, kwargs)
                raise
            yield response or True
        else:
            error = 'Unrecognized loopback message: {} {}'.format(header, data)
            self.log_error(error)
            yield error

    def _handle_loopback_safe(self, data):
        """
        Handle incoming messages in the _loopback_safe socket.
        """
        method, args, kwargs = cloudpickle.loads(data)
        try:
            response = getattr(self, method)(*args, **kwargs)
        except Exception as error:
            yield format_method_exception(error, method, args, kwargs)
            raise
        yield response

    def _loopback_reqrep(self, socket, data_to_send):
        """
        Create a temporary connection a loopback socket and send a request.

        Returns
        -------
        Response obtained from the loopback socket.
        """
        loopback = self._context.socket(zmq.REQ)
        try:
            loopback.connect(socket)
            loopback.send_pyobj(data_to_send)
            return loopback.recv_pyobj()
        except zmq.error.ContextTerminated:
            pass
        finally:
            loopback.close(linger=0.)

    def _loopback(self, header, data=None):
        """
        Send a message to the loopback socket.
        """
        if not self._running:
            raise NotImplementedError()
        data = cloudpickle.dumps((header, data))
        return self._loopback_reqrep('inproc://loopback', data)

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
        if not self._running:
            raise RuntimeError(
                'Agent must be running to safely execute methods!')
        data = cloudpickle.dumps((method, args, kwargs))
        return self._loopback_reqrep('inproc://_loopback_safe', data)

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
            alias = unique_identifier()
        self._timer[alias] = timer
        return alias

    def after(self, delay, method, *args, alias=None, **kwargs):
        """
        Execute an action after a delay.

        Parameters
        ----------
        delay : float
            Execute the action after `delay` seconds.
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
        timer = after(delay, self._loopback,
                      'EXECUTE_METHOD', (method, args, kwargs))
        if not alias:
            alias = unique_identifier()
        self._timer[alias] = timer
        return alias

    def stop_all_timers(self):
        """
        Stop all currently running timers.
        """
        for alias in self.list_timers():
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
        Return a list with all timer aliases currently running.

        Returns
        -------
        list (str)
            A list with all the timer aliases currently running.
        """
        return list(self._timer.keys())

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
        self._keep_alive = False
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
        if self._registered(logger):
            logger_kind = AgentAddressKind(self._address[logger].kind)
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
        Return the address of a socket given by its alias.

        Parameters
        ----------
        alias : str
            Alias of the socket whose address is to be retrieved.

        Returns
        -------
        AgentAddress
            Address of the agent socket associated with the alias.
        """
        return self._address[alias]

    def _register(self, socket, address, alias=None, handler=None):
        """
        Internally register a connection as a socket-address pair.

        Parameters
        ----------
        socket : zmq.Socket
            The socket object to store.
        address : str, AgentAddress
            The address the socket is bound to.
        alias : str, default is None
            Optional alias for the connection.
        handler : function(s)
            Optional handler(s) for the socket. This can be a list or a
            dictionary too.
        """
        assert not self._registered(address), \
            'Socket is already registered!'
        if not alias:
            alias = address
        self._socket[alias] = socket
        self._socket[address] = socket
        self._socket[socket] = socket
        self._address[alias] = address
        self._address[socket] = address
        self._address[address] = address
        if handler is not None:
            self._poller.register(socket, zmq.POLLIN)
            if address.kind in ('SUB', 'SYNC_SUB'):
                self.subscribe(socket, handler)
            else:
                self._set_handler(socket, handler)

    def _set_handler(self, socket, handler, update=False):
        """
        Set the socket handler(s).

        Parameters
        ----------
        socket : zmq.Socket
            Socket to set its handler(s).
        handler : function(s)
            Handler(s) for the socket. This can be a list or a dictionary too.
        """
        if update:
            try:
                self._handler[socket].update(self._curated_handlers(handler))
            except KeyError:
                self._handler[socket] = self._curated_handlers(handler)
        else:
            self._handler[socket] = self._curated_handlers(handler)

    def _curated_handlers(self, handler):
        if isinstance(handler, (list, tuple)):
            return [self._curate_handler(h) for h in handler]
        if isinstance(handler, dict):
            return {k: self._curate_handler(v) for k, v in handler.items()}
        return self._curate_handler(handler)

    def _curate_handler(self, handler):
        if isinstance(handler, str):
            handler = getattr(self, handler)
        function_type = (types.FunctionType, types.BuiltinFunctionType)
        if isinstance(handler, function_type):
            return handler
        method_type = (types.MethodType, types.BuiltinMethodType)
        if isinstance(handler, method_type):
            return unbound_method(handler)
        raise TypeError('Unknown handler type "%s"' % type(handler))

    def _registered(self, address):
        """
        Check if an address is already registered.
        """
        return address in self._socket

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
        kind = guess_kind(kind)
        transport = transport \
            or self._transport \
            or config['TRANSPORT']
        serializer = serializer \
            or self._serializer \
            or config['SERIALIZER']
        if isinstance(kind, AgentAddressKind):
            return self._bind_address(kind, alias, handler, addr, transport,
                                      serializer)
        else:
            return self._bind_channel(kind, alias, handler, addr, transport,
                                      serializer)

    def _bind_address(self, kind, alias=None, handler=None, addr=None,
                      transport=None, serializer=None):
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
        validate_handler(handler, required=kind.requires_handler())
        socket = self._context.socket(kind.zmq())
        addr = self._bind_socket(socket, addr=addr, transport=transport)
        server_address = AgentAddress(transport, addr, kind, 'server',
                                      serializer)
        self._register(socket, server_address, alias, handler)
        # SUB sockets are a special case
        if kind == 'SUB':
            self.subscribe(server_address, handler)
        return server_address

    def _bind_channel(self, kind, alias=None, handler=None, addr=None,
                      transport=None, serializer=None):
        """
        Bind process for channels.

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
        AgentChannel
            The channel where the agent binded to.
        """
        if kind == 'ASYNC_REP':
            validate_handler(handler, required=True)
            socket = self._context.socket(zmq.PULL)
            addr = self._bind_socket(socket, addr=addr, transport=transport)
            server_address = AgentAddress(transport, addr, 'PULL', 'server',
                                          serializer)
            channel = AgentChannel(kind, receiver=server_address, sender=None)
            self._register(socket, channel, alias, handler)
            return channel
        if kind == 'SYNC_PUB':
            if addr:
                raise NotImplementedError()
            if not addr:
                addr = (None, None)
            pull_address = self.bind('PULL_SYNC_PUB',
                                     addr=addr[0],
                                     handler=handler,
                                     transport=transport,
                                     serializer=serializer)
            pub_socket = self._context.socket(zmq.PUB)
            aux = self._bind_socket(pub_socket, addr=addr[1],
                                    transport=transport)
            pub_address = AgentAddress(transport, aux, 'PUB', 'server',
                                       serializer)
            channel = AgentChannel(kind, receiver=pull_address,
                                   sender=pub_address)
            self._register(pub_socket, channel, alias=alias)
            return channel
        else:
            raise NotImplementedError('Unsupported channel kind %s!' % kind)

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
            return self._bind_socket_tcp(socket, addr=addr)
        if not addr:
            addr = unique_identifier().decode('ascii')
        if transport == 'ipc':
            addr = config['IPC_DIR'] / addr
        socket.bind('%s://%s' % (transport, addr))
        return addr

    def _bind_socket_tcp(self, socket, addr):
        """
        Bind a socket using the TCP transport and corresponding address.

        Parameters
        ----------
        socket : zmq.Socket
            Socket to bind.
        addr : str, default is None
            The address to bind to.

        Returns
        -------
        addr : str
            The address where the socket binded to.
        """
        host, port = address_to_host_port(addr)
        if not host:
            host = self._host
        if not port:
            uri = 'tcp://%s' % host
            port = socket.bind_to_random_port(uri)
            addr = host + ':' + str(port)
        else:
            socket.bind('tcp://%s' % (addr))
        return addr

    def connect(self, server, alias=None, handler=None):
        """
        Connect to a server agent address.

        Parameters
        ----------
        server : AgentAddress
            Agent address to connect to.
        alias : str, default is None
            Optional alias for the new address.
        handler, default is None
            If the new socket receives input messages, the handler/s is/are to
            be set with this parameter.
        """
        if isinstance(server, AgentAddress):
            return self._connect_address(server, alias=alias, handler=handler)
        else:
            return self._connect_channel(server, alias=alias, handler=handler)

    def _connect_address(self, server_address, alias=None, handler=None):
        """
        Connect to a basic ZMQ agent address.

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
        validate_handler(handler,
                         required=client_address.kind.requires_handler())
        if self._registered(client_address):
            self._connect_old(client_address, alias, handler)
        else:
            self._connect_and_register(client_address, alias, handler)
        if client_address.kind == 'SUB':
            if not alias:
                alias = client_address
            self.subscribe(alias, handler)
        return client_address

    def _connect_channel(self, channel, alias=None, handler=None):
        """
        Connect to a server agent channel.

        Parameters
        ----------
        channel : AgentChannel
            Agent channel to connect to.
        alias : str, default is None
            Optional alias for the new channel.
        handler, default is None
            If the new socket receives input messages, the handler/s is/are to
            be set with this parameter.
        """
        kind = channel.kind
        if kind == 'ASYNC_REP':
            return self._connect_channel_async_rep(channel,
                                                   handler=handler,
                                                   alias=alias)
        if kind == 'SYNC_PUB':
            return self._connect_channel_sync_pub(channel,
                                                  handler=handler,
                                                  alias=alias)
        raise NotImplementedError('Unsupported channel kind %s!' % kind)

    def _connect_channel_async_rep(self, channel, handler, alias=None):
        """
        Connect to a server agent ASYNC_REP channel.

        Parameters
        ----------
        channel : AgentChannel
            Agent channel to connect to.
        alias : str, default is None
            Optional alias for the new channel.
        handler, default is None
            If the new socket receives input messages, the handler/s is/are to
            be set with this parameter.
        """
        # Connect PUSH-PULL (asynchronous REQ-REP)
        pull_address = channel.receiver
        self._connect_address(pull_address, alias=alias, handler=None)
        if self._registered(channel):
            raise NotImplementedError('Tried to (re)connect a channel')
        self._connect_and_register(pull_address.twin(), alias=alias,
                                   register_as=channel)
        # Create socket for receiving responses
        uuid = unique_identifier()
        addr = self.bind('PULL', alias=uuid,
                         handler=self._handle_async_requests)
        self._async_req_uuid[pull_address] = uuid
        self._async_req_uuid[pull_address.twin()] = uuid
        self._async_req_uuid[addr] = uuid
        self._async_req_handler[uuid] = handler

    def _connect_channel_sync_pub(self, channel, handler, alias=None):
        """
        Connect to a server agent SYNC_PUB channel.

        Parameters
        ----------
        channel : AgentChannel
            Agent channel to connect to.
        alias : str, default is None
            Optional alias for the new channel.
        handler, default is None
            If the new socket receives input messages, the handler/s is/are to
            be set with this parameter.
        """
        # Connect PUSH-PULL (synchronous PUB-SUB)
        client_channel = channel.twin()
        self._connect_address(channel.receiver, alias=alias, handler=None)
        if self._registered(channel):
            raise NotImplementedError('Tried to (re)connect a channel')
        self._connect_and_register(client_channel.sender, alias=alias,
                                   register_as=client_channel)
        # Create socket for receiving responses
        pub_address = channel.sender
        assert pub_address.kind == 'PUB'
        uuid = unique_identifier()
        topic_handlers = {}
        if isinstance(handler, dict):
            topic_handlers = topics_to_bytes(handler, uuid=channel.uuid)
        else:
            topic_handlers[channel.uuid] = handler
        topic_handlers[uuid] = self._handle_async_requests
        addr = self.connect(pub_address, alias=uuid,
                            handler=topic_handlers)
        assert addr.kind == 'SUB'
        self._async_req_uuid[channel.receiver] = uuid
        self._async_req_uuid[client_channel.sender] = uuid
        self._async_req_uuid[addr] = uuid
        self._async_req_handler[uuid] = handler
        return client_channel

    def _connect_old(self, client_address, alias=None, handler=None):
        if handler is not None:
            raise NotImplementedError('Undefined behavior!')
        self._socket[alias] = self._socket[client_address]
        self._address[alias] = client_address
        return client_address

    def _connect_and_register(self, client_address, alias=None, handler=None,
                              register_as=None):
        """
        Establish and register a new connection.

        Parameters
        ----------
        client_address : AgentAddress
            The address to connect to.
        alias : str
            Optional alias for the connection.
        handler : function(s)
            Optional handler(s) for the socket.
        register_as
            What the socket should be registered as (usually an AgentAddress).
        """
        if not register_as:
            register_as = client_address
        socket = self._context.socket(client_address.kind.zmq())
        socket.connect('%s://%s' % (client_address.transport,
                                    client_address.address))
        self._register(socket, register_as, alias, handler)
        return client_address

    def _handle_async_requests(self, data):
        """
        Receive and process an async request.
        """
        address_uuid, uuid, response = data
        if uuid not in self._pending_requests:
            error = 'Received response for an unknown request! %s' % uuid
            self.log_warning(error)
            return
        handler = self._pending_requests.pop(uuid)

        if isinstance(handler, str):
            handler = getattr(self, handler)
            handler(response)
        else:
            handler(self, response)

    def subscribe(self, alias: str,
                  handler: Dict[Union[bytes, str], Any]) -> None:
        """
        Subscribe a SUB/SYNC_SUB socket given by its alias to the given
        topics, and leave the handlers prepared internally.

        Parameters
        ----------
        alias
            Alias of the new subscriber socket.
        handler
            A dictionary in which the keys represent the different topics
            and the values the actual handlers. If, instead of a dictionary,
            a single handler is given, it will be used to subscribe the agent
            to any topic.
        """
        if not isinstance(handler, dict):
            handler = {'': handler}

        curated_handlers = topics_to_bytes(handler)

        # Subscribe to topics
        for topic in curated_handlers:
            self._subscribe_to_topic(alias, topic)

        # Reset handlers
        if isinstance(self._address[alias], AgentChannel):
            channel = self._address[alias]
            sub_address = channel.receiver
            uuid = channel.twin_uuid
            curated_handlers = topics_to_bytes(handler, uuid=uuid)
            self._set_handler(self._socket[sub_address], curated_handlers,
                              update=True)
        else:
            self._set_handler(self._socket[alias], curated_handlers,
                              update=True)

    def unsubscribe(self, alias: str, topic: Union[bytes, str]) -> None:
        """
        Unsubscribe a SUB/SYNC_SUB socket given by its alias from a given
        specific topic, and delete its entry from the handlers dictionary.

        If instead of a single topic, a tuple or a list of topics is passed,
        the agent will unsubscribe from all the supplied topics.
        """
        if isinstance(topic, (tuple, list)):
            for t in topic:
                self.unsubscribe(alias, t)
            return

        topic = topic_to_bytes(topic)

        if isinstance(self._address[alias], AgentAddress):
            self._socket[alias].setsockopt(zmq.UNSUBSCRIBE, topic)
            del self._handler[self._socket[alias]][topic]
        elif isinstance(self._address[alias], AgentChannel):
            channel = self._address[alias]
            sub_address = channel.receiver
            treated_topic = channel.twin_uuid + topic
            self._socket[sub_address].setsockopt(zmq.UNSUBSCRIBE,
                                                 treated_topic)
            del self._handler[self._socket[sub_address]][treated_topic]
        else:
            raise NotImplementedError('Unsupported address type %s!' %
                                      self._address[alias])

    def _subscribe_to_topic(self, alias: str, topic: Union[bytes, str]):
        """
        Do the actual ZeroMQ subscription of a socket given by its alias to
        a specific topic. This method only makes sense to be called on
        SUB/SYNC_SUB sockets.

        Note that the handler is not set within this function.
        """
        topic = topic_to_bytes(topic)

        if isinstance(self._address[alias], AgentAddress):
            self._socket[alias].setsockopt(zmq.SUBSCRIBE, topic)
        elif isinstance(self._address[alias], AgentChannel):
            channel = self._address[alias]
            sub_address = channel.receiver
            treated_topic = channel.uuid + topic
            self._socket[sub_address].setsockopt(zmq.SUBSCRIBE, treated_topic)
        else:
            raise NotImplementedError('Unsupported address type %s!' %
                                      self._address[alias])

    def idle(self):
        """
        This function is to be executed when the agent is idle.

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

    def get_attr(self, name: str):
        """
        Return the specified attribute of the agent.

        Parameters
        ----------
        name
            Name of the attribute to be retrieved.
        """
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

    def execute_as_function(self, function, *args, **kwargs):
        """
        Execute a function passed as parameter.
        """
        return function(*args, **kwargs)

    def execute_as_method(self, function, *args, **kwargs):
        """
        Execute a function as a method, without adding it to the set of
        agent methods.
        """
        return function(self, *args, **kwargs)

    def _loop(self):
        """
        Agent's main loop.

        This loop is executed until the `_keep_alive` attribute is False
        or until an error occurs.
        """
        while self._keep_alive:
            try:
                if self._iterate():
                    break
            except zmq.error.ContextTerminated:
                self._die_now = True
                break

    def _iterate(self):
        """
        Agent's main iteration.

        This iteration is normally executed inside the main loop.

        The agent is polling all its sockets for input data. It will wait
        for `poll_timeout`; after this period, the method `idle` will be
        executed before polling again.

        Returns
        -------
        int
            1 if an error occurred during the iteration (we would expect this
            to happen if an interruption occurs during polling).

            0 otherwise.
        """
        try:
            events = dict(self._poller.poll(self._poll_timeout))
        except zmq.ZMQError as error:
            # Raise the exception in case it is not due to SIGINT
            if error.errno == errno.EINTR:
                return 1
            raise

        if not events:
            # Agent is idle
            self.idle()
            return 0

        self._process_events(events)

        return 0

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
        if serializer.requires_separator:
            sep = message.index(TOPIC_SEPARATOR) + 1
            message = memoryview(message)[sep:]

        return deserialize_message(message=message, serializer=serializer)

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
            self._process_single_event(socket)

    def _process_single_event(self, socket):
        """
        Process a socket's event.

        Parameters
        ----------
        socket : zmq.Socket
            Socket that generated the event.
        """
        data = socket.recv()
        address = self._address[socket]
        if address.kind == 'SUB':
            self._process_sub_event(socket, address, data)
        elif address.kind == 'PULL':
            self._process_pull_event(socket, address, data)
        elif address.kind == 'REP':
            self._process_rep_event(socket, address, data)
        else:
            self._process_single_event_complex(address, socket, data)

    def _process_single_event_complex(self, address, socket, data):
        """
        Process a socket's event for complex sockets (channels).

        Parameters
        ----------
        address : AgentAddress or AgentChannel
            Agent address or channel associated to the socket.
        socket : zmq.Socket
            Socket that generated the event.
        data
            Received in the socket.
        """
        if address.kind == 'ASYNC_REP':
            self._process_async_rep_event(socket, address, data)
        elif address.kind == 'PULL_SYNC_PUB':
            self._process_sync_pub_event(socket, address.channel, data)
        else:
            raise NotImplementedError('Unsupported kind %s!' % address.kind)

    def _process_rep_event(self, socket, addr, data):
        """
        Process a REP socket's event.

        Parameters
        ----------
        socket : zmq.Socket
            Socket that generated the event.
        addr : AgentAddress
            AgentAddress associated with the socket that generated the event.
        data : bytes
            Data received on the socket.
        """
        message = deserialize_message(message=data, serializer=addr.serializer)
        handler = self._handler[socket]
        if inspect.isgeneratorfunction(handler):
            generator = handler(self, message)
            socket.send(serialize_message(next(generator), addr.serializer))
            execute_code_after_yield(generator)
        else:
            reply = handler(self, message)
            socket.send(serialize_message(reply, addr.serializer))

    def _process_async_rep_event(self, socket, channel, data):
        """
        Process a ASYNC_REP socket's event.

        Parameters
        ----------
        socket : zmq.Socket
            Socket that generated the event.
        channel : AgentChannel
            AgentChannel associated with the socket that generated the event.
        data : bytes
            Data received on the socket.
        """
        message = deserialize_message(message=data,
                                      serializer=channel.serializer)
        address_uuid, request_uuid, data, address = message
        client_address = address.twin()
        if not self._registered(client_address):
            self.connect(address)
        handler = self._handler[socket]
        is_generator = inspect.isgeneratorfunction(handler)
        if is_generator:
            generator = handler(self, data)
            reply = next(generator)
        else:
            reply = handler(self, data)
        self.send(client_address, (address_uuid, request_uuid, reply))
        if is_generator:
            execute_code_after_yield(generator)

    def _process_sync_pub_event(self, socket, channel, data):
        """
        Process a SYNC_PUB socket's event.

        Parameters
        ----------
        socket : zmq.Socket
            Socket that generated the event.
        channel : AgentChannel
            AgentChannel associated with the socket that generated the event.
        data : bytes
            Data received on the socket.
        """
        message = deserialize_message(message=data,
                                      serializer=channel.serializer)
        address_uuid, request_uuid, data = message
        handler = self._handler[socket]
        is_generator = inspect.isgeneratorfunction(handler)
        if is_generator:
            generator = handler(self, data)
            reply = next(generator)
        else:
            reply = handler(self, data)
        message = (address_uuid, request_uuid, reply)
        self._send_channel_sync_pub(channel=channel,
                                    message=message,
                                    topic=address_uuid,
                                    general=False)
        if is_generator:
            execute_code_after_yield(generator)

    def _process_pull_event(self, socket, addr, data):
        """
        Process a PULL socket's event.

        Parameters
        ----------
        socket : zmq.Socket
            Socket that generated the event.
        addr : AgentAddress
            AgentAddress associated with the socket that generated the event.
        data : bytes
            Data received on the socket.
        """
        message = deserialize_message(message=data, serializer=addr.serializer)
        handler = self._handler[socket]
        if not isinstance(handler, (list, dict, tuple)):
            handler = [handler]
        for h in handler:
            h(self, message)

    def _process_sub_event(self, socket, addr, data):
        """
        Process a SUB socket's event.

        Parameters
        ----------
        socket : zmq.Socket
            Socket that generated the event.
        addr : AgentAddress
            AgentAddress associated with the socket that generated the event.
        data : bytes
            Data received on the socket.
        """
        handlers = self._handler[socket]

        message = self._process_sub_message(addr.serializer, data)

        for topic in handlers:
            if not data.startswith(topic):
                continue
            # Call the handler (with or without the topic)
            handler = handlers[topic]
            nparams = len(inspect.signature(handler).parameters)
            if nparams == 2:
                handler(self, message)
            elif nparams == 3:
                handler(self, message, topic)

    def send(self, address, message, topic=None, handler=None, wait=None,
             on_error=None):
        """
        Send a message through the specified address.

        Note that replies in a REQREP pattern do not use this function in
        order to be sent.

        Parameters
        ----------
        address : AgentAddress or AgentChannel
            The address to send the message through.
        message
            The message to be sent.
        topic : str
            The topic, in case it is relevant (i.e.: for PUB sockets).
        handler : function, method or string
            Code that will be executed on input messages if relevant (i.e.:
            for asynchronous requests in channels).
        wait : float
            For channel requests, wait at most this number of seconds for a
            response from the server.
        on_error : function, method or string
            Code to be executed if `wait` is passed and the response is not
            received.
        """
        address = self._address[address]
        if isinstance(address, AgentChannel):
            return self._send_channel(channel=address,
                                      message=message,
                                      topic=topic,
                                      handler=handler,
                                      wait=wait,
                                      on_error=on_error)
        if isinstance(address, AgentAddress):
            return self._send_address(address=address,
                                      message=message,
                                      topic=topic)
        raise NotImplementedError('Unsupported address type %s!' % address)

    def _send_address(self, address, message, topic=None):
        """
        Send a message through a specific address.
        """
        message = serialize_message(message=message,
                                    serializer=address.serializer)
        if address.kind == 'PUB':
            if topic is None:
                topic = ''
            topic = topic_to_bytes(topic)
            message = compose_message(message=message,
                                      topic=topic,
                                      serializer=address.serializer)
        self._socket[address].send(message)

    def _send_channel(self, channel, message, topic, handler, wait, on_error):
        """
        Send a message through a specific channel.
        """
        kind = channel.kind
        if kind == 'ASYNC_REP':
            return self._send_channel_async_rep(channel=channel,
                                                message=message,
                                                wait=wait,
                                                on_error=on_error,
                                                handler=handler)
        if kind == 'SYNC_PUB':
            return self._send_channel_sync_pub(channel=channel,
                                               message=message,
                                               topic=topic)
        if kind == 'SYNC_SUB':
            return self._send_channel_sync_sub(channel, message, topic,
                                               handler, wait, on_error)

        raise NotImplementedError('Unsupported channel kind %s!' % kind)

    def _send_channel_async_rep(self, channel, message, wait, on_error,
                                handler=None):
        """
        Send a message through an ASYNC_REP channel.
        """
        address = channel.receiver
        address_uuid = self._async_req_uuid[address]
        request_uuid = unique_identifier()
        if handler is not None:
            self._pending_requests[request_uuid] = handler
        else:
            self._pending_requests[request_uuid] = \
                self._async_req_handler[address_uuid]
        receiver_address = self._address[address_uuid]
        message = (address_uuid, request_uuid, message, receiver_address)
        message = serialize_message(message=message,
                                    serializer=channel.serializer)
        self._socket[channel].send(message)
        self._wait_received(wait, uuid=request_uuid, on_error=on_error)

    def _send_channel_sync_pub(self, channel, message, topic=None,
                               general=True):
        """
        Send a message through a SYNC_PUB channel.
        """
        message = serialize_message(message=message,
                                    serializer=channel.serializer)
        if topic is None:
            topic = ''
        topic = topic_to_bytes(topic)
        if general:
            topic = channel.uuid + topic
        message = compose_message(message=message,
                                  topic=topic,
                                  serializer=channel.serializer)
        self._socket[channel].send(message)

    def _send_channel_sync_sub(self, channel, message, topic, handler, wait,
                               on_error):
        """
        Send a message through a SYNC_SUB channel.
        """
        address = channel.receiver
        address_uuid = self._async_req_uuid[address]
        request_uuid = unique_identifier()
        if handler is None:
            raise ValueError('No handler for SYNC_PUB request')
        self._pending_requests[request_uuid] = handler
        message = (address_uuid, request_uuid, message)
        self._send_address(channel.sender, message)
        self._wait_received(wait, uuid=request_uuid, on_error=on_error)
        return

    def _check_received(self, uuid, wait, on_error):
        """
        Check if the requested information has been received.

        Parameters
        ----------
        uuid : str
            Request identifier.
        wait : float
            The total number of seconds since the request was made.
        on_error : function, method or string
            Code to be executed in case a response was not received for the
            request in time. If not provided, it will simply log a warning.
        """
        if uuid not in self._pending_requests:
            return

        del self._pending_requests[uuid]
        if not on_error:
            warning = 'Did not receive request {} after {} seconds'.format(
                uuid, wait)
            self.log_warning(warning)
            return
        on_error(self)

    def _wait_received(self, wait, uuid, on_error):
        """
        Set up a timer to check a response was received for a given request
        after a defined time lapse.

        Parameters
        ----------
        uuid : str
            Request identifier.
        wait : float
            The total number of seconds to wait for the response.
        on_error : function, method or string
            Code to be executed in case a response was not received for the
            request in time. If not provided, it will simply log a warning.
        """
        if not wait:
            return
        return self.after(wait, '_check_received', uuid, wait, on_error)

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
        message = self._socket[address].recv()
        serializer = self._address[address].serializer
        return deserialize_message(message=message, serializer=serializer)

    def send_recv(self, address, message):
        """
        This method is only used in REQREP communication patterns.
        """
        self.send(address, message)
        return self.recv(address)

    def is_running(self):
        """
        Returns a boolean indicating whether the agent is running or not.
        """
        return self._running

    @Pyro4.oneway
    def run(self):
        """
        Start the main loop.
        """
        # A loopback socket where, for example, timers are processed
        self.bind('REP', alias='loopback', addr='loopback',
                  handler=self._handle_loopback, transport='inproc',
                  serializer='pickle')

        # This in-process socket handles safe access to
        # memory from other threads (i.e. when using Pyro proxies).
        self.bind('REP', alias='_loopback_safe', addr='_loopback_safe',
                  handler=self._handle_loopback_safe, transport='inproc',
                  serializer='pickle')

        self._running = True
        self.before_loop()
        try:
            self._loop()
        except Exception as error:
            self._running = False
            msg = 'An exception occurred while running! (%s)\n' % error
            msg += format_exception()
            self.log_error(msg)
            raise
        self._running = False
        if self._die_now:
            self._die()

    def shutdown(self):
        """
        Cleanly stop and shut down the agent assuming the agent is running.

        Will let the main thread do the tear down.
        """
        self.log_info('Stopping...')
        self._keep_alive = False
        self._die_now = True

    def kill(self):
        """
        Force shutdown of the agent.

        If the agent is running the ZMQ context is terminated to allow the
        main thread to quit and do the tear down.
        """
        self.stop_all_timers()
        if self._running:
            self._context.term()
        else:
            self._die(linger=0)

    def _die(self, linger=None):
        """
        Tear down the agent. Last action before ending existence.

        - Stop timers.
        - Close all external sockets.
        - Shutdown the Pyro daemon.
        """
        self.stop_all_timers()
        self.close_all(linger=linger)
        self._pyroDaemon.shutdown()

    def _get_unique_external_zmq_sockets(self):
        """
        Return an iterable containing all the zmq.Socket objects from
        `self.socket` which are not internal, without repetition.

        Originally, a socket was internal if its alias was one of the
        following:
            - loopback
            - _loopback_safe
            - inproc://loopback
            - inproc://_loopback_safe

        However, since we are storing more than one entry in the `self.socket`
        dictionary per zmq.socket (by storing its AgentAddress, for example),
        we need a way to simply get all non-internal zmq.socket objects, and
        this is precisely what this function does.
        """
        reserved = ('loopback', '_loopback_safe', 'inproc://loopback',
                    'inproc://_loopback_safe')
        external_sockets = []

        for k, v in self._socket.items():
            if isinstance(k, zmq.sugar.socket.Socket):
                continue
            if isinstance(k, AgentAddress) and k.address in reserved:
                continue
            if k in reserved:
                continue

            external_sockets.append(v)

        return set(external_sockets)

    def has_socket(self, alias):
        """
        Return whether the agent has the passed socket internally stored.
        """
        return alias in self._socket

    def _delete_socket_entries(self, entries):
        for entry in entries:
            del self._socket[entry]

    def _cleanup_ipc_socket_files(self, address):
        """
        Make sure no IPC socket files are left in the file system.
        """
        if isinstance(address, AgentChannel):
            candidates = [address.receiver, address.sender]
        else:
            candidates = [address]
        for candidate in candidates:
            if candidate is None or candidate.role != 'server':
                continue
            with contextlib.suppress(FileNotFoundError):
                candidate.address.unlink()

    def _close_socket(self, socket, linger):
        """
        Close a socket using the provided linger value.
        """
        linger = get_linger(linger)
        socket.close(linger=linger)
        address = self._address[socket]
        if address.transport == 'ipc':
            self._cleanup_ipc_socket_files(address)

    def close(self, alias, linger=None):
        """
        Close a socket given its alias and clear its entry from the
        `Agent.socket` dictionary.
        """
        socket = self._socket[alias]
        # Each socket might be pointed by different keys
        entries_to_delete = []
        for k, v in self._socket.items():
            if v == socket:
                entries_to_delete.append(k)
        self._delete_socket_entries(entries_to_delete)
        self._close_socket(socket, linger=linger)

    def close_all(self, linger=None):
        """
        Close all non-internal zmq sockets.
        """
        # Each socket might be pointed by different keys
        sockets_to_delete = []
        for socket in self._get_unique_external_zmq_sockets():
            sockets_to_delete.append(socket)
            self._close_socket(socket, linger=linger)

        entries_to_delete = []
        for k, v in self._socket.items():
            if v in sockets_to_delete:
                entries_to_delete.append(k)
        self._delete_socket_entries(entries_to_delete)

    def ping(self):
        """
        A test method to check the readiness of the agent. Used for testing
        purposes, where timing is very important. Do not remove.
        """
        return 'pong'


class AgentProcess(multiprocessing.Process):
    """
    Agent class. Instances of an Agent are system processes which
    can be run independently.
    """
    def __init__(self, name='', nsaddr=None, addr=None, serializer=None,
                 transport=None, base=Agent, attributes=None):
        super().__init__()
        self.name = name
        self._daemon = None
        self._host, self.port = address_to_host_port(addr)
        if self.port is None:
            self.port = 0
        self.nsaddr = nsaddr
        self._serializer = serializer
        self._transport = transport
        self.base = cloudpickle.dumps(base)
        self._shutdown_event = multiprocessing.Event()
        self._queue = multiprocessing.Queue()
        self._sigint = False
        self.attributes = attributes

    def run(self):
        """
        Begin execution of the agent process and start the main loop.
        """
        # Capture SIGINT
        signal.signal(signal.SIGINT, self._sigint_handler)

        try:
            ns = NSProxy(self.nsaddr)
            self._daemon = Pyro4.Daemon(self._host, self.port)
            self.base = cloudpickle.loads(self.base)
            self.agent = self.base(name=self.name, host=self._host,
                                   serializer=self._serializer,
                                   transport=self._transport,
                                   attributes=self.attributes)
        except Exception:
            self._queue.put(format_exception())
            return

        self.name = self.agent.name
        uri = self._daemon.register(self.agent)
        try:
            ns.register(self.name, uri, safe=True)
        except Pyro4.errors.NamingError:
            self._queue.put(format_exception())
            return
        finally:
            ns.release()

        self._queue.put('STARTED:' + self.name)

        self._daemon.requestLoop(lambda: not self._shutdown_event.is_set())
        self._daemon.unregister(self.agent)

        self._teardown()

    def _remove_from_nameserver(self):
        """
        Make sure to remove the agent's name from the name server.
        """
        while True:
            try:
                ns = NSProxy(self.nsaddr)
                ns.remove(self.name)
                ns.release()
            except PyroError as error:
                time.sleep(0.1)
                continue
            break

    def _teardown(self):
        """
        Remove self from the name server address book, close daemon and die.
        """
        if not self._sigint:
            # Clean teardown
            self._remove_from_nameserver()

        self.agent._killed = True
        self._daemon.close()

    def start(self):
        """
        Start the system process.

        Raises
        ------
        RuntimeError
            If an error occurred when initializing the daemon.
        """
        super().start()
        status = self._queue.get()
        if not status.startswith('STARTED'):
            raise RuntimeError('An error occurred while creating the daemon!' +
                               '\n===============\n'.join(['', status, '']))

        return status.partition(':')[-1]

    def kill(self):
        """
        Force kill the agent process.
        """
        self._shutdown_event.set()
        if self._daemon:
            self._daemon.shutdown()

    def _sigint_handler(self, signal, frame):
        """
        Handle interruption signals.
        """
        self._sigint = True
        self.kill()


def run_agent(name='', nsaddr=None, addr=None, base=Agent, serializer=None,
              transport=None, safe=None, attributes=None):
    """
    Ease the agent creation process.

    This function will create a new agent, start the process and then run
    its main loop through a proxy.

    Parameters
    ----------
    name : str, default is ''
        Agent name or alias.
    nsaddr : SocketAddress, default is None
        Name server address.
    addr : SocketAddress, default is None
        New agent address, if it is to be fixed.
    transport : str, AgentAddressTransport, default is None
        Transport protocol.
    safe : bool, default is None
        Use safe calls by default from the Proxy.
    attributes : dict, default is None
        A dictionary that defines initial attributes for the agent.

    Returns
    -------
    proxy
        A proxy to the new agent.
    """
    if not nsaddr:
        nsaddr = os.environ.get('OSBRAIN_NAMESERVER_ADDRESS')
    agent = AgentProcess(name=name, nsaddr=nsaddr, addr=addr, base=base,
                         serializer=serializer, transport=transport,
                         attributes=attributes)
    agent_name = agent.start()

    proxy = Proxy(agent_name, nsaddr, safe=safe)
    proxy.run()
    proxy.wait_for_running()

    return proxy
