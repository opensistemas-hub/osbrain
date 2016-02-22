"""
Implementation of address-related features.
"""
import zmq


class AgentAddressRole(str):
    """
    Agent's address role class. It can either be 'server' or 'client'.
    """
    def __new__(cls, value):
        if value not in ['server', 'client']:
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
        """
        Returns
        -------
        SocketAddress
            Agent address as a SocketAddress object. This means `kind` and
            `role` information are lost.
        """
        return SocketAddress(self.host, self.port)
