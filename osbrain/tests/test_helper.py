"""
Test file for functionality implemented in `osbrain/tests/common.py`.
"""
import time
from threading import Timer

import pytest

from osbrain import Agent
from osbrain import run_agent
from osbrain.helper import agent_dies
from osbrain.helper import attribute_match_all
from osbrain.helper import last_received_endswith
from osbrain.helper import logger_received
from osbrain.helper import wait_agent_attr
from osbrain.helper import wait_agent_condition
from osbrain.helper import wait_condition


class SugarAddict():
    def __init__(self):
        self.glucose = 0

    def feed_candy(self):
        self.glucose += 1

    def happy(self):
        return bool(self.glucose)

    def sad(self):
        return not bool(self.glucose)


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


@pytest.mark.parametrize('data,match', [
    (dict(attribute=[], length=1), False),
    (dict(attribute=[], data=1), False),
    (dict(attribute=[], value=[]), True),
    (dict(attribute=[1, 2], length=2, data=2), True),
    (dict(attribute=[1, 2], length=2, data=3), False),
    (dict(attribute=[1, 2], length=3, data=2), False),
    (dict(attribute={'foo'}, length=1), True),
    (dict(attribute={'foo'}, data='foo'), True),
    (dict(attribute={'foo'}, value={'foo'}), True),
    (dict(attribute=42, value=14), False),
    (dict(attribute=42, value=42), True),
    (dict(attribute=[1, 2, 3], endswith=[2, 3]), True),
    (dict(attribute=[1, 2, 3], endswith=[3, 3]), False),
    (dict(attribute='abcde', endswith='cde'), True),
    (dict(attribute='abcde', endswith='ade'), False),
], ids=[
    'List length mismatch',
    'Data not in list',
    'List exact value',
    'Data in list and list length',
    'Data not in list with length match',
    'Data in list with length mismatch',
    'Dictionary attribute length',
    'Key in dictionary',
    'Dictionary exact value',
    'Integer value mismatch',
    'Integer value match',
    'List ending with',
    'List not ending with',
    'String ending with',
    'String not ending with',
])
def test_attribute_match_all(data, match):
    """
    Test `attribute_match_all` function.
    """
    result = attribute_match_all(**data)
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


@pytest.mark.parametrize('delay,timeout,result', [
    (1, 0.5, False),
    (0.5, 1, True),
])
def test_wait_condition(delay, timeout, result):
    """
    Test the `wait_agent_condition` function.
    """
    kid = SugarAddict()
    Timer(delay, kid.feed_candy).start()
    assert wait_condition(kid.happy, timeout=timeout) == result


@pytest.mark.parametrize('delay,timeout,result', [
    (1, 0.5, False),
    (0.5, 1, True),
])
def test_wait_condition_negate(delay, timeout, result):
    """
    Test the negated `wait_agent_condition` function.
    """
    kid = SugarAddict()
    Timer(delay, kid.feed_candy).start()
    assert wait_condition(kid.sad, negate=True, timeout=timeout) == result


def test_wait_agent_condition(nsproxy):
    """
    Test `wait_agent_condition` function.
    """
    class Counter(Agent):
        def on_init(self):
            self.count = 0
            self.log = []

        def increment(self):
            self.log.append(self.count)
            self.count += 1
            time.sleep(0.1)

    def log_length(agent, size):
        return len(agent.log) > size

    a0 = run_agent('a0', base=Counter)
    a0.each(0., 'increment')

    assert not wait_agent_condition(a0, log_length, size=4, timeout=0.2)
    assert wait_agent_condition(a0, log_length, size=10, timeout=1.)
    assert wait_agent_condition(a0, lambda agent: agent.count > 8, timeout=0.)


def test_last_received_endswith(nsproxy):
    """
    Test `last_received_endswith` function.
    """
    agent = run_agent('a0')
    assert not agent.execute_as_method(last_received_endswith, 'foo')
    agent.set_attr(received=[])
    assert not agent.execute_as_method(last_received_endswith, 'foo')
    agent.set_attr(received=['bar'])
    assert not agent.execute_as_method(last_received_endswith, 'foo')
    agent.set_attr(received=['foo', 'bar'])
    assert not agent.execute_as_method(last_received_endswith, 'foo')
    agent.set_attr(received=['bar', 'foo'])
    assert agent.execute_as_method(last_received_endswith, 'foo')
