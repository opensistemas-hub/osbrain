"""
Miscellaneous utilities.
"""
import time
import sched
import threading

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


def periodic(scheduler, interval, action, args=()):
    """
    Run a scheduler periodically.

    This function will run forever and blocking.

    Parameters
    ----------
    scheduler : sched.scheduler
        Scheduler to run.
    interval : numeric
        Delay to apply to the scheduler.
    action
        Action to execute by the scheduler.
    args, default is ()
        Arguments for the action.
    """
    scheduler.enter(interval, 1, periodic,
                    (scheduler, interval, action, args))
    action(*args)


def repeat(interval, action, args=()):
    """
    Repeat an action forever after a given number of seconds.

    If a sequence of events takes longer to run than the time available
    before the next event, the repeater will simply fall behind.

    This function is executed in a separate thread.

    Parameters
    ----------
    interval : float
        Number of seconds between executions.
    action
        To be taken after the interval.
    args : tuple, default is ()
        Arguments for the action.

    Returns
    -------
    threading.Thread
        Thread running the repeat task.
    """
    scheduler = sched.scheduler(time.time, time.sleep)
    periodic(scheduler, interval, action, args)
    t = threading.Thread(target=scheduler.run)
    t.start()
    return t
