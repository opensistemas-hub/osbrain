"""
Implementation of logging-related features.
"""
import os
from .core import BaseAgent
from .core import run_agent


def pyro_log():
    """
    Set environment variables to activate Pyro logging. The log level is
    set to "DEBUG".
    """
    os.environ['PYRO_LOGFILE'] = 'pyro_osbrain.log'
    os.environ['PYRO_LOGLEVEL'] = 'DEBUG'


class Logger(BaseAgent):
    """
    Specialized BaseAgent for logging. Binds a `SUB` socket and starts
    logging incoming messages.
    """
    def on_init(self):
        self.log_history_info = []
        self.log_history_warning = []
        self.log_history_error = []
        self.log_history_debug = []
        self.log_history = []
        handlers = {
            'INFO': self.log_handler,
            'WARNING': self.log_handler,
            'ERROR': self.log_handler,
            'DEBUG': self.log_handler
        }
        self.bind('SUB', 'sub', handlers)

    def log_handler(self, message, topic):
        """
        Handle incoming log messages.
        """
        if topic == 'INFO':
            self.log_history_info.append(message)
        elif topic == 'WARNING':
            self.log_history_warning.append(message)
        elif topic == 'ERROR':
            self.log_history_error.append(message)
        elif topic == 'DEBUG':
            self.log_history_debug.append(message)
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
