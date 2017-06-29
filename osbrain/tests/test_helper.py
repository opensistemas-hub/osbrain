"""
Test file for functionality implemented in `osbrain/tests/common.py`.
"""
import pytest

from osbrain import run_agent
from osbrain import Agent
from osbrain.helper import logger_received
from osbrain.helper import agent_dies
from osbrain.helper import attribute_match_all
from osbrain.helper import wait_agent_attr

from common import nsproxy  # pragma: no flakes
from common import agent_logger  # pragma: no flakes


def test_agent_dies(nsproxy):
    """
    The function `agent_dies` should return `False` if the agent does not die
    after a timeout.
    """
    run_agent('a0')
    assert not agent_dies('a0', nsproxy, timeout=0.5)


def test_sync_agent_logger(agent_logger):
    """
    After synchronizing and agent and a logger, a message logged should
    always be received by the logger.
    """
    a0, logger = agent_logger
    a0.log_info('asdf')
    assert logger_received(logger, message='asdf')


def test_logger_received(agent_logger):
    """
    The function `logger_received` should return `False` if the message is
    not received after a timeout.
    """
    a0, logger = agent_logger
    assert not logger_received(logger, 'asdf', log_name='log_history_error')


def test_logger_received_position(agent_logger):
    """
    The function `logger_received` should accept a parameter to specify the
    exact position where the regular expression should be matching.
    """
    a0, logger = agent_logger
    a0.log_info('m0')
    a0.log_info('m1')
    a0.log_info('m2')
    # Any position
    assert logger_received(logger, message='m2')
    assert logger_received(logger, message='m1')
    assert logger_received(logger, message='m0')
    # -1 position
    assert logger_received(logger, message='m2', position=-1, timeout=0.1)
    assert not logger_received(logger, message='m1', position=-1, timeout=0.1)
    assert not logger_received(logger, message='m0', position=-1, timeout=0.1)
    # -2 position
    assert not logger_received(logger, message='m2', position=-2, timeout=0.1)
    assert logger_received(logger, message='m1', position=-2, timeout=0.1)
    assert not logger_received(logger, message='m0', position=-2, timeout=0.1)
    # 0 position (important to test vs. None)
    assert not logger_received(logger, message='m2', position=0, timeout=0.1)
    assert not logger_received(logger, message='m1', position=0, timeout=0.1)
    assert not logger_received(logger, message='m0', position=0, timeout=0.1)


def test_logger_received_newline(agent_logger):
    """
    The `'.'` special character in `logger_received` regular expressions
    should match newline characters too.
    """
    a0, logger = agent_logger
    a0.log_info('foo\nbar')
    assert logger_received(logger, message='foo.*bar')


def test_logger_received_count(agent_logger):
    """
    The function `logger_received` actually returns an integer with the total
    number of matches.
    """
    a0, logger = agent_logger
    a0.log_info('foo bar')
    a0.log_info('foo beer')
    a0.log_info('foo asdf bar')
    # Make sure logger receives the last message
    assert logger_received(logger, message='foo asdf bar')
    # Start counting...
    assert logger_received(logger, message='foo') == 3
    assert logger_received(logger, message='foo b') == 2
    assert logger_received(logger, message='foo beer') == 1
    assert logger_received(logger, message='bar') == 2
    assert logger_received(logger, message='foo.*bar') == 2


@pytest.mark.parametrize('attribute,length,data,value,match', [
    ([], 1, None, None, False),
    ([], None, 1, None, False),
    ([], None, None, [], True),
    ([1, 2], 2, 2, None, True),
    ([1, 2], 2, 3, None, False),
    ([1, 2], 3, 2, None, False),
    ({'foo'}, 1, None, None, True),
    ({'foo'}, None, 'foo', None, True),
    ({'foo'}, None, None, {'foo'}, True),
    (42, None, None, 14, False),
    (42, None, None, 42, True),
])
def test_attribute_match_all(attribute, length, data, value, match):
    """
    Test `attribute_match_all` function.
    """
    result = attribute_match_all(attribute, length=length, data=data,
                                 value=value)
    assert result == match


def test_wait_agent_attr(nsproxy):
    """
    Test `wait_agent_attr` function.
    """
    class Client(Agent):
        def set_received_method(self, value):
            self.received = value

    a0 = run_agent('a0', base=Client)

    # Named attribute, zero timeout
    a0.set_attr(x=[])
    assert not wait_agent_attr(a0, 'x', length=1, timeout=0.)

    # Default attribute, timeout
    a0.set_attr(received=0)
    a0.after(1, 'set_received_method', 42)
    assert not wait_agent_attr(a0, value=42, timeout=0.)
    assert wait_agent_attr(a0, value=42, timeout=2.)
