import time
import Pyro4
from Pyro4.errors import NamingError
from .common import address_to_host_port
from .address import SocketAddress


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


class NSProxy(Pyro4.core.Proxy):
    def __init__(self, nsaddr=None, timeout=3):
        nshost, nsport = address_to_host_port(nsaddr)
        if nsaddr is None:
            nshost = '127.0.0.1'
            nsport = 9090
        # Make sure name server exists
        locate_ns(nsaddr, timeout)
        super().__init__('PYRONAME:Pyro.NameServer@%s:%s' % (nshost, nsport))

    def addr(self):
        return SocketAddress(self._pyroUri.host, self._pyroUri.port)

    def release(self):
        self._pyroRelease()
