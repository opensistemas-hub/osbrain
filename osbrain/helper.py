"""
Helper functions for osbrain (usually for testing purposes).
"""
import time
from uuid import uuid4


def logger_received(logger, log_name, message, timeout=1.):
    """
    Check if a logger receives a message.

    Parameters
    ----------
    logger : Proxy
        Proxy to the logger.
    log_name : str
        The name of the attribue to look for in the logger.
    message : anything
        Message to look for in the log. Can be a partial match.
    timeout : float
        After this number of seconds the function will return `False`.

    Returns
    -------
    bool
        Whether the logger received the message or not.
    """
    t0 = time.time()
    while True:
        time.sleep(0.01)
        log_history = logger.get_attr(log_name)
        if len(log_history) and message in log_history[-1]:
            break
        if timeout and time.time() - t0 > timeout:
            return False
    return True


def sync_agent_logger(agent, logger):
    """
    Make sure and agent and a logger are synchronized.

    An agent is synchronized with its logger when we make sure the logger has
    started receiving messages from the agent.

    Parameters
    ----------
    agent : Proxy
        Proxy to the agent.
    logger : Proxy
        Proxy to the logger.
    """
    while not len(logger.get_attr('log_history_info')):
        message = str(uuid4())
        agent.log_info(message)
        time.sleep(0.01)
    while message not in logger.get_attr('log_history_info')[-1]:
        time.sleep(0.01)


def agent_dies(agent, nsproxy, timeout=1.):
    """
    Check if an agent dies within a given period.

    Parameters
    ----------
    agent : str
        Name of the agent, as registered in the name server.
    nsproxy : NSProxy
        Proxy to the name server.
    timeout : float
        After this number of seconds the function will return `False`.

    Returns
    -------
    bool
        Whether the agent died (was unregistered from the name server) within
        the given period.
    """
    t0 = time.time()
    while True:
        time.sleep(0.01)
        if agent not in nsproxy.agents():
            break
        if timeout and time.time() - t0 > timeout:
            return False
    return True


def attribute_match(attribute, length=None, data=None, value=None):
    """
    Check if an attribute matches any condition:

    - Minimum length.
    - Contains an item.
    - Is exactly a value.

    Parameters
    ----------
    attribute : anything
        The attribute to match against.
    length : int, default is None
        Return True if the attribute has this minimum length.
    data : anything, default is None
        Return True if the attribute contains this value.
    value : anything, default is None
        Return True if the attribute contains this value.

    Returns
    -------
    bool
        Whether the attribute matches any condition.
    """
    assert length is not None or data is not None or value is not None, \
        'No condition passed! will return False always...'
    if length is not None and len(attribute) >= length:
        return True
    if data is not None and data in attribute:
        return True
    if value is not None and attribute == value:
        return True
    return False


def wait_agent_attr(agent, name='received', length=None, data=None, value=None,
                    timeout=3):
    """
    Wait for an agent's attribute, to:

    - Reach a minimum length.
    - Contain a particular item.
    - Become a given value.

    Parameters
    ----------
    agent : Proxy
        A proxy to the agent.
    name : str, default is `'received'`
        Name of the agent's attribute to look for (should be a list).
    length : int, default is None
        If specified, wait until the attribute reaches this length.
    data : anything, default is None
        If specified, wait until the attribute contains this element.
    value : anything, default is None
        If specified, wait until the attribute becomes this value.
    timeout : float, default is 3
        After this number of seconds the function will return `False`.
    """
    t0 = time.time()
    while True:
        attribute = agent.get_attr(name)
        if attribute_match(attribute, length=length, data=data, value=value):
            return True
        if time.time() - t0 > timeout:
            break
        time.sleep(0.01)
    return False
