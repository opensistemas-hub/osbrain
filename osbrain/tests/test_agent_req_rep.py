"""
Test file for REQ-REP communication pattern.
"""
import time

from osbrain import run_agent
from osbrain import run_logger
from osbrain.helper import logger_received
from osbrain.helper import sync_agent_logger

from common import nsproxy  # pragma: no flakes


def test_return(nsproxy):
    """
    REQ-REP pattern using a handler that returns a value.
    """
    def rep_handler(agent, message):
        return message

    a0 = run_agent('a0')
    a1 = run_agent('a1')
    addr = a0.bind('REP', handler=rep_handler)
    a1.connect(addr, alias='request')
    response = a1.send_recv('request', 'Hello world')
    assert response == 'Hello world'


def test_lambda(nsproxy):
    """
    REQ-REP pattern using a lambda handler.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    addr = a0.bind('REP', handler=lambda agent, message: 'x' + message)
    a1.connect(addr, alias='request')
    response = a1.send_recv('request', 'Hello world')
    assert response == 'xHello world'


def test_yield(nsproxy):
    """
    REQ-REP pattern using a handler that yields a value. This is useful in
    order to generate an early reply.
    """
    def reply_early(agent, message):
        yield message
        time.sleep(agent.delay)
        agent.delay = 'ok'

    delay = 1
    a0 = run_agent('a0')
    a0.set_attr(delay=delay)
    a1 = run_agent('a1')

    addr = a0.bind('REP', handler=reply_early)
    a1.connect(addr, alias='request')

    t0 = time.time()
    response = a1.send_recv('request', 'Working!')
    assert time.time() - t0 < delay / 2.
    assert response == 'Working!'
    assert a0.get_attr('delay') == delay
    # Sleep so that the replier has had time to update
    time.sleep(delay + 0.5)
    assert a0.get_attr('delay') == 'ok'


def test_multiple_yield(nsproxy):
    """
    A replier must only make use of yield once.
    """
    def yield_twice(agent, message):
        yield message
        yield 'Derp'

    logger = run_logger('logger')
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    a0.set_logger(logger)
    sync_agent_logger(agent=a0, logger=logger)

    addr = a0.bind('REP', handler=yield_twice)
    a1.connect(addr, alias='request')

    response = a1.send_recv('request', 'Hello world!')
    # Response is received successfully
    assert response == 'Hello world!'
    # Replier should crash
    assert logger_received(logger, log_name='log_history_error',
                           message='yielded more than once')
