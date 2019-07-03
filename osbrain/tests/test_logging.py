"""
Logging module tests.
"""
import os

from osbrain import run_agent
from osbrain import run_logger
from osbrain.helper import logger_received
from osbrain.logging import pyro_log


def test_logging_level(nsproxy):
    """
    Logging with different log levels should result in different logs being
    filled.
    """
    agent = run_agent('agent')
    agent.set_attr(_DEBUG=True)
    logger = run_logger('logger')
    agent.set_logger(logger)
    i = 0
    while not len(logger.get_attr('log_history')):
        i += 1
        agent.log_info(i)
    assert logger_received(logger, message=r'\): %s' % i, position=-1)
    before = len(logger.get_attr('log_history'))
    agent.log_info('some information')
    agent.log_warning('some warning')
    agent.log_error('some error')
    agent.log_debug('some debug')
    # Log values
    assert logger_received(logger, 'some information', 'log_history_info', -1)
    assert logger_received(logger, 'some warning', 'log_history_warning', -1)
    assert logger_received(logger, 'some error', 'log_history_error', -1)
    assert logger_received(logger, 'some debug', 'log_history_debug', -1)
    # Log sizes
    assert len(logger.get_attr('log_history_info')) == 1 + before
    assert len(logger.get_attr('log_history_warning')) == 1
    assert len(logger.get_attr('log_history_error')) == 1
    assert len(logger.get_attr('log_history_debug')) == 1


def test_pyro_log():
    """
    Calling the pyro_log function should set some environment variables to
    start Pyro logging into a file.
    """
    assert os.environ.get('PYRO_LOGFILE', None) is None
    assert os.environ.get('PYRO_LOGLEVEL', None) is None
    pyro_log()
    assert os.environ.get('PYRO_LOGFILE', None) == 'pyro_osbrain.log'
    assert os.environ.get('PYRO_LOGLEVEL', None) == 'DEBUG'
    del os.environ['PYRO_LOGFILE']
    del os.environ['PYRO_LOGLEVEL']
