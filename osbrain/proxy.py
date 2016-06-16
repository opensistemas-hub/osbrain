"""
Implementation of proxy-related features.
"""
import sys
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
    time0 = time.time()
    while time.time() - time0 < timeout:
        try:
            Pyro4.locateNS(host, port)
            return nsaddr
        except NamingError:
            continue
    raise NamingError('Could not find name server after timeout!')


class Proxy(Pyro4.core.Proxy):
    """
    A proxy to access remote agents.

    Parameters
    ----------
    name : str
        Proxy name, as registered in the name server.
    nsaddr : SocketAddress, str
        Name server address.
    timeout : float
        Timeout, in seconds, to wait until the agent is discovered.
    """
    def __init__(self, name, nsaddr=None, timeout=3.):
        nshost, nsport = address_to_host_port(nsaddr)
        # Make sure name server exists
        locate_ns(nsaddr)
        time0 = time.time()
        while time.time() - time0 < timeout:
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
        while time.time() - time0 < timeout:
            try:
                self.test()
            except NamingError:
                continue
            break
        else:
            raise NamingError('Could not test agent!')

    def release(self):
        """
        Release the connection to the Pyro daemon.
        """
        self._pyroRelease()

    def pyro_addr(self):
        """
        Returns
        -------
        SocketAddress
            The socket address of the Pyro server.
        """
        return SocketAddress(self._pyroUri.host, self._pyroUri.port)

    def _pyroInvoke(self, methodname, args, kwargs, flags=0, objectId=None):
        try:
            result = super()._pyroInvoke(
                methodname, args, kwargs, flags=flags, objectId=objectId)
        except:
            sys.stdout.write(''.join(Pyro4.util.getPyroTraceback()))
            sys.stdout.flush()
            raise
        if methodname == 'set_method':
            for method in args:
                self._pyroMethods.add(method.__name__)
            for name, method in kwargs.items():
                self._pyroMethods.add(name)
        if methodname == 'set_attr':
            for name in kwargs:
                self._pyroAttrs.add(name)
        return result

    def __getattr__(self, name):
        if name in self._pyroAttrs:
            return self.get_attr(name)
        else:
            return super().__getattr__(name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            return super().__setattr__(name, value)
        else:
            kwargs = {name: value}
            return self.set_attr(**kwargs)


class NSProxy(Pyro4.core.Proxy):
    """
    A proxy to access a name server.

    Parameters
    ----------
    nsaddr : SocketAddress, str
        Name server address.
    timeout : float
        Timeout, in seconds, to wait until the name server is discovered.
    """
    def __init__(self, nsaddr=None, timeout=3):
        nshost, nsport = address_to_host_port(nsaddr)
        if nsaddr is None:
            nshost = '127.0.0.1'
            nsport = 9090
        # Make sure name server exists
        locate_ns(nsaddr, timeout)
        super().__init__('PYRONAME:Pyro.NameServer@%s:%s' % (nshost, nsport))

    def addr(self):
        """
        Returns
        -------
        SocketAddress
            The socket address of the Pyro server.
        """
        return SocketAddress(self._pyroUri.host, self._pyroUri.port)

    def release(self):
        """
        Release the connection to the Pyro daemon.
        """
        self._pyroRelease()

    def proxy(self, name, timeout=3.):
        """
        Get a proxy to access an agent registered in the name server.

        Parameters
        ----------
        name : str
            Proxy name, as registered in the name server.
        timeout : float
            Timeout, in seconds, to wait until the agent is discovered.

        Returns
        -------
        Proxy
            A proxy to access an agent registered in the name server.
        """
        return Proxy(name, nsaddr=self.addr(), timeout=timeout)
