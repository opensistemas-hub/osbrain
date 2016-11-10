"""
Logging module tests.
"""
import os
import time

from osbrain import run_agent
from osbrain import run_logger
from osbrain.logging import pyro_log

from common import nsproxy  # pragma: no flakes


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
    while not '): %s' % i in logger.get_attr('log_history')[0]:
        time.sleep(0.01)
    before = len(logger.get_attr('log_history'))
    agent.log_info('some information')
    agent.log_warning('some warning')
    agent.log_error('some error')
    agent.log_debug('some debug')
    after = before
    while not after - before == 4:
        after = len(logger.get_attr('log_history'))
    # Log size
    assert len(logger.get_attr('log_history_info')) == 1 + before
    assert len(logger.get_attr('log_history_warning')) == 1
    assert len(logger.get_attr('log_history_error')) == 1
    assert len(logger.get_attr('log_history_debug')) == 1
    # Log message
    assert 'some information' in logger.get_attr('log_history_info')[-1]
    assert 'some warning' in logger.get_attr('log_history_warning')[-1]
    assert 'some error' in logger.get_attr('log_history_error')[-1]
    assert 'some debug' in logger.get_attr('log_history_debug')[-1]


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
