import os
from .core import Agent
from .core import Proxy


def pyro_log():
    os.environ["PYRO_LOGFILE"] = "pyro_osbrain.log"
    os.environ["PYRO_LOGLEVEL"] = "DEBUG"


def log_handler(agent, message):
    agent.log_history.append(message)


def run_logger(name, nsaddr=None, addr=None):
    """
    Ease the logger creation process.

    This function will create a new logger, start the process and then run
    its main loop through a proxy.

    Parameters
    ----------
    name : str
        Logger name or alias.
    nsaddr : SocketAddress, default is None
        Name server address.
    addr : SocketAddress, default is None
        New logger address, if it is to be fixed.

    Returns
    -------
    proxy
        A proxy to the new logger.
    """
    Agent(name, nsaddr, addr).start()
    proxy = Proxy(name, nsaddr)
    proxy.set_attr('log_history', [])
    # TODO: handle INFO, ERROR... differently?
    handlers = {
        'INFO': log_handler,
        'ERROR': log_handler
    }
    proxy.bind('SUB', 'logger_sub_socket', handlers)
    proxy.run()
    return proxy
