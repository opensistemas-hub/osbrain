"""
Implementation of address-related features.
"""
from ipaddress import ip_address

import zmq


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
        Returns
        -------
        AgentAddressRole
            The twin role of the current one; `server` would be the twin
            of `client` and viceversa.
        """
        if self == 'server':
            return self.__class__('client')
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
        if kind not in cls.ZMQ_STR_CONVERSION:
            raise ValueError('Invalid address kind "%s"!' % kind)
        if isinstance(kind, str):
            kind = cls.ZMQ_STR_CONVERSION[kind]
        return super().__new__(cls, kind)

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
        if self.ZMQ_STR_CONVERSION[self] in ('REQ', 'PUSH', 'PUB'):
            return False
        return True

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


class AgentAddressSerializer(str):
    """
    Agent's address serializer class.

    Each communication channel will have a serializer.

    Note that for `raw` message passing, everything must be on bytes, and the
    programmer is the one responsible for converting data to bytes.

    Parameters
    ----------
    serializer_type : str
        Serializer type (i.e.: 'raw', 'pickle'...).
    """
    def __new__(cls, value):
        if value not in ('raw', 'pickle'):
            raise ValueError('Invalid serializer type %s!' % value)
        return super().__new__(cls, value)


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
    addr : str
        Agent address.
    kind : str, AgentAddressKind
        Agent kind.
    role : str, AgentAddressRole
        Agent role.
    serializer : str
        Agent serializer type.

    Attributes
    ----------
    addr : int
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
            hash(self.kind) ^ hash(self.role)

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
        Returns
        -------
        AgentAddress
            The twin address of the current one; while the `host` and `port`
            are kept for the twin, the `kind` and `role` change to their
            corresponding twins, according to the rules defined in the
            respective classes.
        """
        kind = self.kind.twin()
        role = self.role.twin()
        return self.__class__(self.transport, self.address, kind, role,
                              self.serializer)
