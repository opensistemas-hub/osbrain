"""
Miscellaneous utilities.
"""
from .address import SocketAddress


class LogLevel(str):
    """
    Identifies the log level: ERROR, WARNING, INFO, DEBUG.
    """
    def __new__(cls, value):
        if value not in ['ERROR', 'WARNING', 'INFO', 'DEBUG']:
            raise ValueError('Incorrect value "%s"!' % value)
        return super().__new__(cls, value)


def address_to_host_port(addr=None):
    """
    Try to convert a string or SocketAddress to a (host, port) tuple.

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
    if isinstance(addr, SocketAddress):
        return (addr.host, addr.port)
    if not isinstance(addr, str):
        try:
            addr = addr.addr()
            return (addr.host, addr.port)
        except:
            raise ValueError('Unsupported address type "%s"!' % type(addr))
    aux = addr.split(':')
    if len(aux) == 1:
        port = None
    else:
        port = int(aux[-1])
    host = aux[0]
    return (host, port)


def unbound_method(method):
    """
    Returns
    -------
    function
        Unbounded function.
    """
    return getattr(method.__self__.__class__, method.__name__)
