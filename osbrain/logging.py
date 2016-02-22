import os
from .core import Agent
from .core import BaseAgent
from .core import run_agent
from .proxy import Proxy


def pyro_log():
    os.environ["PYRO_LOGFILE"] = "pyro_osbrain.log"
    os.environ["PYRO_LOGLEVEL"] = "DEBUG"


class Logger(BaseAgent):
    def on_init(self):
        self.log_history = []
        handlers = {
            'INFO': self.log_handler,
            'ERROR': self.log_handler
        }
        self.bind('SUB', 'logger_sub_socket', handlers)

    def log_handler(self, message, topic):
        # TODO: handle INFO, ERROR... differently?
        self.log_history.append(message)


def run_logger(name, nsaddr=None, addr=None, base=Logger):
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
    return run_agent(name, nsaddr, addr, base)
