"""
Test file for functionality implemented in `osbrain/tests/common.py`.
"""
from osbrain import run_agent
from osbrain import run_logger

from common import nsproxy  # pragma: no flakes
from common import logger_received
from common import sync_agent_logger
from common import agent_dies


def test_agent_dies(nsproxy):
    """
    The function `agent_dies` should return `False` if the agent does not die
    after a timeout.
    """
    run_agent('a0')
    assert not agent_dies('a0', nsproxy, timeout=0.5)


def test_sync_agent_logger(nsproxy):
    """
    After synchronizing and agent and a logger, a message logged should
    always be received by the logger.
    """
    a0 = run_agent('a0')
    logger = run_logger('logger')
    a0.set_logger(logger)
    sync_agent_logger(agent=a0, logger=logger)
    a0.log_info('asdf')
    assert logger_received(logger, 'log_history_info', message='asdf')


def test_logger_received(nsproxy):
    """
    The function `logger_received` should return `False` if the message is
    not received after a timeout.
    """
    a0 = run_agent('a0')
    logger = run_logger('logger')
    a0.set_logger(logger)
    sync_agent_logger(agent=a0, logger=logger)
    assert not logger_received(logger, 'log_history_error', message='asdf')
