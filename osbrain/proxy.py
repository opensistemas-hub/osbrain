"""
Implementation of proxy-related features.
"""
import os
import sys
import time

import Pyro4
from Pyro4.errors import ConnectionClosedError
from Pyro4.errors import NamingError
from Pyro4.message import FLAGS_ONEWAY

from . import config
from .address import address_to_host_port
from .address import SocketAddress


def locate_ns(nsaddr, timeout=3.):
    """
    Locate a name server to ensure it actually exists.

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
    time0 = time.time()
    while True:
        try:
            Pyro4.locateNS(host, port)
            return nsaddr
        except NamingError:
            if time.time() - time0 < timeout:
                time.sleep(0.1)
                continue
            raise TimeoutError('Could not locate the name server!')


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
    safe : bool, default is None
        Use safe calls by default. When not set, osbrain default's
        `osbrain.config['SAFE']` is used.
    """
    def __init__(self, name, nsaddr=None, timeout=3., safe=None):
        if not nsaddr:
            nsaddr = os.environ.get('OSBRAIN_NAMESERVER_ADDRESS')
        nshost, nsport = address_to_host_port(nsaddr)
        # Make sure name server exists
        locate_ns(nsaddr)
        time0 = time.time()
        super().__init__('PYRONAME:%s@%s:%s' % (name, nshost, nsport))
        if safe is not None:
            self._default_safe = safe
        else:
            self._default_safe = config['SAFE']
        self._safe = self._default_safe
        self._next_oneway = False
        while not self._ready_or_timeout(time0, timeout):
            continue

    def _ready_or_timeout(self, time0, timeout):
        """
        Check if the proxy is ready or raise after a timeout.

        Parameters
        ----------
        time0 : float
            Timestamp (in seconds) to take as the initial time.
        timeout : float
            Time (in seconds) allowed after `time0` before raising an
            exception.
        """
        try:
            self.unsafe.ping()
        except Exception:
            time.sleep(0.1)
            if time.time() - time0 < timeout:
                return False
            raise
        return True

    def wait_for_running(self, timeout=3.):
        """
        Wait until the agent is running.

        Parameters
        ----------
        timeout : float
            Raise and exception if the agent is not running after this number
            of seconds. Use a negative value to wait forever.

        Raises
        ------
        TimeoutError
            If the agent is not running after the given timeout.

        Returns
        -------
        Proxy
            The object itself.
        """
        time0 = time.time()
        while not self.is_running():
            if timeout >= 0 and time.time() - time0 > timeout:
                msg = 'Timed out while waiting for the agent to be running'
                raise TimeoutError(msg)
            time.sleep(.01)

        return self

    def __getstate__(self):
        return super().__getstate__() + \
            (self._next_oneway, self._default_safe, self._safe)

    def __setstate__(self, state):
        super().__setstate__(state[:-3])
        self._next_oneway = state[-3]
        self._default_safe = state[-2]
        self._safe = state[-1]

    def __setattr__(self, name, value):
        if name in ('_safe', '_default_safe', '_next_oneway'):
            return super(Pyro4.core.Proxy, self).__setattr__(name, value)
        if name.startswith('_'):
            return super().__setattr__(name, value)
        kwargs = {name: value}
        return self.set_attr(**kwargs)

    def __getattr__(self, name):
        if name in self._pyroAttrs:
            return self.get_attr(name)
        return super().__getattr__(name)

    def release(self):
        """
        Release the connection to the Pyro daemon.
        """
        self._pyroRelease()

    def nsaddr(self):
        """
        Get the socket address of the name server.

        Returns
        -------
        SocketAddress
            The socket address.
        """
        return SocketAddress(self._pyroUri.host, self._pyroUri.port)

    @property
    def safe(self):
        """
        Make the next remote method call be safe.

        Returns
        -------
        The proxy itself.
        """
        self._safe = True
        return self

    @property
    def unsafe(self):
        """
        Make the next remote method call be unsafe.

        Returns
        -------
        The proxy itself.
        """
        self._safe = False
        return self

    @property
    def oneway(self):
        """
        Make the next remote method call be one way.

        Returns
        -------
        The proxy itself.
        """
        self._next_oneway = True
        return self

    def _pyroInvoke(self, methodname, args, kwargs,
                    flags=0, objectId=None):  # flake8: noqa
        """
        Wrapper around `_remote_call` to safely execute methods on remote
        objects.
        """
        try:
            result = self._remote_call(
                methodname, args, kwargs, flags, objectId)
        except Exception:
            sys.stdout.write(''.join(Pyro4.util.getPyroTraceback()))
            sys.stdout.flush()
            raise
        finally:
            self._safe = self._default_safe
            self._next_oneway = False
        self._post_invoke(methodname, args, kwargs)
        return result

    def _is_safe_method(self, methodname):
        """
        Check if a remote method can be called safely.

        Parameters
        ----------
        methodname : str
            The name of the method to evaluate.

        Returns
        -------
        bool
            Whether the method can be safely called.
        """
        return (methodname in self._pyroMethods and
                not methodname.startswith('_') and
                methodname not in ('run', 'get_attr', 'kill', 'safe_call',
                                   'concurrent', 'is_running'))

    def _remote_call(self, methodname, args, kwargs, flags, objectId):
        """
        Call a remote method from the proxy.
        """
        if self._next_oneway:
            flags |= FLAGS_ONEWAY
            result = super()._pyroInvoke(
                methodname, args, kwargs, flags=flags, objectId=objectId)
            return result
        if self._safe and self._is_safe_method(methodname):
            safe_args = [methodname] + list(args)
            result = super()._pyroInvoke(
                'safe_call', safe_args, kwargs,
                flags=flags, objectId=objectId)
            if isinstance(result, Exception):
                raise result
        else:
            result = super()._pyroInvoke(
                methodname, args, kwargs, flags=flags, objectId=objectId)
        return result

    def _post_invoke(self, methodname, args, kwargs):
        """
        After invoking a call, check if the proxy must be modified.

        This could happen if the `set_method` or `set_attr` have been invoked.
        In that case, the method(s) or attribute(s) are added to the proxy's
        available method(s)/attributes(s).
        """
        if methodname == 'set_method':
            self._set_new_available_methods(args, kwargs)
        elif methodname == 'set_attr':
            self._set_new_available_attributes(kwargs)

    def _set_new_available_methods(self, args, kwargs):
        """
        Set new methods available from the proxy.

        Parameters
        ----------
        args : list
            A list of new methods to be made available from the proxy.
        kwargs : dict
            A dictionary with the methods' names and their values.
        """
        for method in args:
            self._pyroMethods.add(method.__name__)
        for name, method in kwargs.items():
            self._pyroMethods.add(name)

    def _set_new_available_attributes(self, kwargs):
        """
        Set new attributes available from the proxy.

        Parameters
        ----------
        kwargs : dict
            A dictionary with the attributes' names and their values.
        """
        for name in kwargs:
            self._pyroAttrs.add(name)


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
        if not nsaddr:
            nsaddr = os.environ.get('OSBRAIN_NAMESERVER_ADDRESS')
        nshost, nsport = address_to_host_port(nsaddr)
        # Make sure name server exists
        locate_ns(nsaddr, timeout)
        ns_name = Pyro4.constants.NAMESERVER_NAME
        super().__init__('PYRONAME:%s@%s:%d' % (ns_name, nshost, nsport))

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

    def addr(self, agent_alias=None, address_alias=None):
        """
        Return the name server address or the address of an agent's socket.

        Parameters
        ----------
        agent_alias : str, default is None
            The alias of the agent to retrieve its socket address.
        address_alias : str, default is None
            The alias of the socket address to retrieve from the agent.

        Returns
        -------
        SocketAddress or AgentAddress
            The name server or agent's socket address.
        """
        if not agent_alias and not address_alias:
            return SocketAddress(self._pyroUri.host, self._pyroUri.port)
        agent = self.proxy(agent_alias)
        addr = agent.addr(address_alias)
        agent.release()
        return addr

    def shutdown_agents(self, timeout=10.):
        """
        Shutdown all agents registered in the name server.

        Parameters
        ----------
        timeout : float, default is 10.
            Timeout, in seconds, to wait for the agents to shutdown.
        """
        # Wait for all agents to be shutdown (unregistered)
        time0 = time.time()
        super()._pyroInvoke('async_shutdown_agents', (self.addr(), ), {})
        while time.time() - time0 <= timeout / 2.:
            if not len(self.agents()):
                return
            time.sleep(0.1)
        super()._pyroInvoke('async_kill_agents', (self.addr(), ), {})
        while time.time() - time0 <= timeout:
            if not len(self.agents()):
                return
            time.sleep(0.1)
        raise TimeoutError(
            'Chances are {} were not shutdown after {} s!'.format(
                self.agents(),
                timeout,
            )
        )

    def shutdown(self, timeout=10.):
        """
        Shutdown the name server. All agents will be shutdown as well.

        Parameters
        ----------
        timeout : float, default is 10.
            Timeout, in seconds, to wait for the agents to shutdown.
        """
        self.shutdown_agents(timeout)
        try:
            super()._pyroInvoke('daemon_shutdown', (), {}, flags=0)
        except ConnectionClosedError:
            pass
