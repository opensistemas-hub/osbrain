from .address import SocketAddress


class LogLevel(str):
    """
    Identifies the log level: ERROR, WARNING, INFO.
    """
    def __new__(cls, value):
        if value not in ['ERROR', 'WARNING', 'INFO']:
            raise ValueError('Incorrect value "%s"!' % value)
        return super().__new__(cls, value)


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


def unbound_method(method):
    return getattr(method.__self__.__class__, method.__name__)
