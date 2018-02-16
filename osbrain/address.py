"""
Implementation of address-related features.
"""
from ipaddress import ip_address

import zmq

from .common import unique_identifier


def address_to_host_port(addr):
    """
    Try to convert an address to a (host, port) tuple.

    Parameters
    ----------
    addr : str, SocketAddress

    Returns
    -------
    tuple
        A (host, port) tuple formed with the corresponding data.
    """
    if addr is None:
        return (None, None)
    # Try the most common case (well-defined types)
    try:
        return _common_address_to_host_port(addr)
    except TypeError:
        pass
    # Try to do something anyway
    if hasattr(addr, 'host') and hasattr(addr, 'port'):
        return (addr.host, addr.port)
    raise ValueError('Unsupported address type "%s"!' % type(addr))


def _common_address_to_host_port(addr):
    """
    Try to convert an address to a (host, port) tuple.

    This function is meant to be used with well-known types. For a more
    general case, use the `address_to_host_port` function instead.

    Parameters
    ----------
    addr : str, SocketAddress, AgentAddress

    Returns
    -------
    tuple
        A (host, port) tuple formed with the corresponding data.
    """
    if isinstance(addr, SocketAddress):
        return (addr.host, addr.port)
    if isinstance(addr, AgentAddress):
        return (addr.address.host, addr.address.port)
    if isinstance(addr, str):
        aux = addr.split(':')
        if len(aux) == 1:
            port = None
        else:
            port = int(aux[-1])
        host = aux[0]
        return (host, port)
    raise TypeError('Unsupported address type "%s"!' % type(addr))


def guess_kind(kind):
    """
    Guess if a kind string is an AgentAddressKind or AgentChannelKind.

    Parameters
    ----------
    kind : str
        The AgentAddressKind or AgentChannelKind in string format.

    Returns
    ----------
    AgentAddressKind or AgentChannelKind
        The actual kind type.
    """
    try:
        return AgentAddressKind(kind)
    except ValueError:
        return AgentChannelKind(kind)


class AgentAddressTransport(str):
    """
    Agent's address transport class. It can be 'tcp', 'ipc' or 'inproc'.
    """
    def __new__(cls, value):
        if value not in ['tcp', 'ipc', 'inproc']:
            raise ValueError('Invalid address transport "%s"!' % value)
        return super().__new__(cls, value)


class AgentAddressRole(str):
    """
    Agent's address role class. It can either be 'server' or 'client'.
    """
    def __new__(cls, value):
        if value not in ['server', 'client']:
            raise ValueError('Invalid address role "%s"!' % value)
        return super().__new__(cls, value)

    def twin(self):
        """
        Get the twin role of the current one. `server` would be the twin
        of `client` and viceversa.

        Returns
        -------
        AgentAddressRole
            The twin role.
        """
        if self == 'server':
            return self.__class__('client')
        return self.__class__('server')


class AgentAddressKind(str):
    """
    Agent's address kind class.

    This kind represents the communication pattern being used by the agent
    address: REP, PULL, PUB...
    """
    TWIN = {
        'REQ': 'REP',
        'REP': 'REQ',
        'PUSH': 'PULL',
        'PULL': 'PUSH',
        'PUB': 'SUB',
        'SUB': 'PUB',
        'PULL_SYNC_PUB': 'PUSH_SYNC_SUB',
        'PUSH_SYNC_SUB': 'PULL_SYNC_PUB',
    }
    ZMQ_KIND_CONVERSION = {
        'REQ': zmq.REQ,
        'REP': zmq.REP,
        'PUSH': zmq.PUSH,
        'PULL': zmq.PULL,
        'PUB': zmq.PUB,
        'SUB': zmq.SUB,
        'PULL_SYNC_PUB': zmq.PULL,
        'PUSH_SYNC_SUB': zmq.PUSH,
    }
    REQUIRE_HANDLER = ('REP', 'PULL', 'SUB', 'PULL_SYNC_PUB')

    def __new__(cls, kind):
        if kind not in cls.TWIN.keys():
            raise ValueError('Invalid address kind "%s"!' % kind)
        return super().__new__(cls, kind)

    def zmq(self):
        """
        Get the equivalent ZeroMQ socket kind.

        Returns
        -------
        int
        """
        return self.ZMQ_KIND_CONVERSION[self]

    def requires_handler(self):
        """
        Whether the Agent's address kind requires a handler or not.
        A socket which processes incoming messages would require a
        handler (i.e. 'REP', 'PULL', 'SUB'...).

        Returns
        -------
        bool
        """
        return self in self.REQUIRE_HANDLER

    def twin(self):
        """
        Get the twin kind of the current one.

        `REQ` would be the twin of `REP` and viceversa, `PUB` would be the
        twin of `SUB` and viceversa, etc.

        Returns
        -------
        AgentAddressKind
            The twin kind of the current one.
        """
        return self.__class__(self.TWIN[self])


class AgentAddressSerializer(str):
    """
    Agent's address serializer class.

    Each communication channel will have a serializer.

    Note that for `raw` message passing, everything must be on bytes, and the
    programmer is the one responsible for converting data to bytes.

    Parameters
    ----------
    serializer_type : str
        Serializer type (i.e.: 'raw', 'pickle', 'cloudpickle', 'dill', 'json').
    """
    SERIALIZER_SIMPLE = ('raw', )
    SERIALIZER_SEPARATOR = ('pickle', 'cloudpickle', 'dill', 'json')

    def __new__(cls, value):
        if value not in cls.SERIALIZER_SIMPLE + cls.SERIALIZER_SEPARATOR:
            raise ValueError('Invalid serializer type %s!' % value)
        return super().__new__(cls, value)

    def __init__(self, value):
        self.requires_separator = value in self.SERIALIZER_SEPARATOR


class SocketAddress(object):
    """
    Socket address information consisting on the host and port.

    Parameters
    ----------
    host : str, ipaddress.IPv4Address
        IP address.
    port : int
        Port number.

    Attributes
    ----------
    host : ipaddress.IPv4Address
        IP address.
    port : int
        Port number.
    """
    def __init__(self, host, port):
        assert isinstance(port, int), \
            'Incorrect parameter port on SocketAddress; expecting type int.'
        self.host = str(ip_address(host))
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


class AgentAddress():
    """
    Agent address information consisting on the transport protocol, address,
    kind and role.

    Parameters
    ----------
    transport : str, AgentAddressTransport
        Agent transport protocol.
    address : str
        Agent address.
    kind : str, AgentAddressKind
        Agent kind.
    role : str, AgentAddressRole
        Agent role.
    serializer : str
        Agent serializer type.

    Attributes
    ----------
    transport : str, AgentAddressTransport
        Agent transport protocol.
    address : str, SocketAddress
        Agent address.
    kind : AgentAddressKind
        Agent kind.
    role : AgentAddressRole
        Agent role.
    serializer : AgentAddressSerializer
        Agent serializer.
    """
    def __init__(self, transport, address, kind, role, serializer):
        if transport == 'tcp':
            address = SocketAddress(*address_to_host_port(address))
        self.transport = AgentAddressTransport(transport)
        self.address = address
        self.kind = AgentAddressKind(kind)
        self.role = AgentAddressRole(role)
        self.serializer = AgentAddressSerializer(serializer)

    def __repr__(self):
        """
        Return the string representation of the AgentAddress.

        Returns
        -------
        representation : str
        """
        return 'AgentAddress(%s, %s, %s, %s, %s)' % \
            (self.transport, self.address, self.kind, self.role,
             self.serializer)

    def __hash__(self):
        return hash(self.transport) ^ hash(self.address) ^ \
            hash(self.kind) ^ hash(self.role) ^ hash(self.serializer)

    def __eq__(self, other):
        if not isinstance(other, AgentAddress):
            return False
        return self.transport == other.transport \
            and self.address == other.address \
            and self.kind == other.kind \
            and self.role == other.role \
            and self.serializer == other.serializer

    def twin(self):
        """
        Return the twin address of the current one.

        While the `host` and `port` are kept for the twin, the `kind` and
        `role` change to their corresponding twins, according to the
        rules defined in the respective classes.

        Returns
        -------
        AgentAddress
            The twin address of the current one.
        """
        kind = self.kind.twin()
        role = self.role.twin()
        return self.__class__(self.transport, self.address, kind, role,
                              self.serializer)


class AgentChannelKind(str):
    """
    Agent's channel kind class.

    This kind represents the communication pattern being used by the agent
    channel: ASYNC_REP, STREAM...
    """
    TWIN = {
        'ASYNC_REP': 'ASYNC_REQ',
        'ASYNC_REQ': 'ASYNC_REP',
        'SYNC_PUB': 'SYNC_SUB',
        'SYNC_SUB': 'SYNC_PUB',
    }

    def __new__(cls, kind):
        if kind not in cls.TWIN.keys():
            raise ValueError('Invalid channel kind "%s"!' % kind)
        return super().__new__(cls, kind)

    def twin(self):
        """
        Get the twin kind of the current one.

        `REQ` would be the twin of `REP` and viceversa, `PUB` would be
        the twin of `SUB` and viceversa, etc.

        Returns
        -------
        AgentChannelKind
        """
        return self.__class__(self.TWIN[self])


class AgentChannel():
    """
    Agent channel information.

    Channels are communication means with sender and receiver in both sides
    (i.e.: PULL+PUB - PUSH-SUB or PULL+PUSH - PUSH+PULL).

    Parameters
    ----------
    kind : AgentChannelKind
        Agent kind.
    sender : str
        First AgentAddress.
    receiver : str
        Second AgentAddress.

    Attributes
    ----------
    kind : AgentChannelKind
        Agent kind.
    sender : str
        First AgentAddress.
    receiver : str
        Second AgentAddress.
    """
    def __init__(self, kind, receiver, sender, twin_uuid=None):
        self.kind = AgentChannelKind(kind)
        self.receiver = receiver
        self.sender = sender
        self.transport = \
            receiver.transport if receiver else sender.transport
        self.serializer = \
            receiver.serializer if receiver else sender.serializer
        self.uuid = unique_identifier()
        self.twin_uuid = twin_uuid
        # Set up pairs
        if sender:
            self.sender.channel = self
        if receiver:
            self.receiver.channel = self

    def __repr__(self):
        """
        Return the string representation of the AgentChannel.

        Returns
        -------
        representation : str
        """
        return 'AgentChannel(kind=%s, receiver=%s, sender=%s)' % \
            (self.kind, self.receiver, self.sender)

    def __hash__(self):
        return hash(self.kind) ^ hash(self.receiver) ^ hash(self.sender)

    def __eq__(self, other):
        if not isinstance(other, AgentChannel):
            return False
        return self.kind == other.kind \
            and self.receiver == other.receiver \
            and self.sender == other.sender

    def twin(self):
        """
        Get the twin channel of the current one.

        Returns
        -------
        AgentChannel
            The twin channel.
        """
        kind = self.kind.twin()
        sender = self.receiver.twin() if self.receiver is not None else None
        receiver = self.sender.twin() if self.sender is not None else None
        return self.__class__(kind=kind, receiver=receiver, sender=sender,
                              twin_uuid=self.uuid)
