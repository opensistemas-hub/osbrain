"""
Miscellaneous utilities.
"""
import time
from threading import Event
from threading import Thread
import traceback
from uuid import uuid4
from typing import Any
from typing import Dict
from typing import Union

from . import config


def unique_identifier() -> bytes:
    """
    Returns
    -------
        A unique identifier that is safe to use in PUB-SUB communication
        patterns (i.e.: does not contain the `osbrain.TOPIC_SEPARATOR`
        character).
    """
    return uuid4().hex.encode()


def format_exception():
    """
    Represent a traceback exception as a string in which all lines start
    with a `|` character.

    Useful for differentiating remote from local exceptions and exceptions
    that where silenced.

    Returns
    -------
    str
        A formatted string containing an exception traceback information.
    """
    begin = '\n|>>>>>>>>'
    end = '\n|<<<<<<<<'
    return begin + '\n| '.join(traceback.format_exc().splitlines()) + end


def format_method_exception(error, method, args, kwargs):
    """
    Represent an exception as a formatted string that includes the name and
    arguments of the method where it occurred, followed by the output of
    `format_exception`.

    Parameters
    ----------
    error : Error
        The exception that was raised.
    method : function
        The method where the exception was raised.
    args
        The arguments of the method call.
    kwargs : dict
        The keyword arguments of the method call.

    Returns
    -------
    str
        The formatted string with the method call and traceback information.
    """
    message = 'Error executing `%s`! (%s)\n' % (method, error)
    message += '\n> method: %s\n> args: %s\n> kwargs: %s\n' % \
        (str(method), str(args), str(kwargs))
    message += format_exception()
    return type(error)(message)


def topic_to_bytes(topic: Union[bytes, str]) -> bytes:
    """
    Return the passed topic as a `bytes` object.
    """
    if isinstance(topic, str):
        topic = topic.encode()
    return topic


def topics_to_bytes(handlers: Dict[Union[bytes, str], Any], uuid: bytes = b''):
    """
    Given some pairs topic/handler, leaves them prepared for making the actual
    ZeroMQ subscription.

    Parameters
    ----------
    handlers
        Contains pairs "topic - handler".
    uuid
        uuid of the SYNC_PUB/SYNC_SUB channel (if applies). For normal
        PUB/SUB communication, this should be `b''`.

    Returns
    -------
    Dict[bytes, Any]
    """
    curated_handlers = {}

    for topic, value in handlers.items():
        topic = topic_to_bytes(topic)
        curated_handlers[uuid + topic] = value

    return curated_handlers


def validate_handler(handler, required):
    """
    Raises a ValueError exception when a required is handler but not present.
    """
    if required and handler is None:
        raise ValueError('This socket requires a handler!')


class LogLevel(str):
    """
    Identifies the log level: ERROR, WARNING, INFO, DEBUG.
    """
    def __new__(cls, value):
        if value not in ['ERROR', 'WARNING', 'INFO', 'DEBUG']:
            raise ValueError('Incorrect value "%s"!' % value)
        return super().__new__(cls, value)


def unbound_method(method):
    """
    Returns
    -------
    function
        Unbounded function.
    """
    return getattr(method.__self__.__class__, method.__name__)


def repeat(interval, action, *args):
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
    Event
        A timer object that can be terminated using the `stop()` method.
    """
    event = Event()

    def loop():
        starttime = time.time()
        while True:
            nexttime = starttime + interval
            action(*args)
            after_action = time.time()
            if event.wait(nexttime - after_action):
                break
            starttime = max(after_action, nexttime)

    Thread(target=loop).start()
    event.stop = event.set

    return event


def after(delay, action, *args):
    """
    Execute an action after a given number of seconds.

    This function is executed in a separate thread.

    Parameters
    ----------
    delay : float
        Number of seconds to delay the action.
    action
        To be taken after the interval.
    args : tuple, default is ()
        Arguments for the action.

    Returns
    -------
    Event
        A timer object that can be terminated using the `stop()` method.
    """
    event = Event()

    def wait():
        if event.wait(delay):
            return
        action(*args)

    Thread(target=wait).start()
    event.stop = event.set

    return event


def get_linger(seconds=None):
    """
    Wrapper to get the linger option from the environment variable.

    Parameters
    ----------
    seconds : float, default is None.
        Linger seconds, in seconds.

    Returns
    -------
    int
        Number of seconds to linger.
        Note that -1 means linger forever.
    """
    if seconds is None:
        seconds = config['LINGER']
    if seconds < 0:
        return -1
    return int(float(seconds) * 1000)
