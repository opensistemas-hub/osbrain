"""
Test file for timers.
"""
import time
import pytest
from osbrain import Agent
from osbrain import run_agent
from osbrain.common import repeat

from common import nsproxy  # pragma: no flakes


def set_received(agent, message, topic=None):
    agent.received = message


@pytest.mark.timeout(1)
def test_repeat_non_blocking():
    """
    A repeated action (i.e. timer) should always be executed in a separate
    thread, even the first execution.
    """
    def foo(x):
        time.sleep(x)

    timer = repeat(1., foo, 2.)
    timer.stop()


def test_repeat_stop():
    """
    Test closing a timer returned by repeat.
    """
    class Bar():
        def __init__(self):
            self.a = 0

        def foo(self):
            self.a += 1

    bar = Bar()
    timer = repeat(0.1, bar.foo)
    time.sleep(1.)
    assert abs(bar.a - 10) <= 1
    timer.stop()
    time.sleep(1.)
    assert abs(bar.a - 10) <= 1


def test_timer_non_blocking_bug(nsproxy):
    """
    A timer call should never block, no matters how long it takes to execute
    the action.
    """
    def long_action(agent):
        time.sleep(1.)
        agent.count += 1

    agent = run_agent('agent')
    agent.set_attr(count=0)
    # Start timer
    t0 = time.time()
    agent.each(0., long_action)
    t1 = time.time()
    assert t1 - t0 < 0.1
    assert agent.get_attr('count') == 0
    time.sleep(1.5)
    assert agent.get_attr('count') > 0


def test_timer_each(nsproxy):
    """
    Test a timer executed periodically.
    """
    def tick(agent):
        agent.send('push', agent.count)
        agent.count += 1

    sender = run_agent('sender')
    sender.set_attr(count=0)
    receiver = run_agent('receiver')
    addr = sender.bind('PUSH', alias='push')
    receiver.connect(addr, handler=set_received)
    # Start timer
    sender.each(0.1, tick)
    time.sleep(2)
    assert abs(receiver.get_attr('received') - 20) <= 1


def test_timer_each_oop(nsproxy):
    """
    Test a timer executed periodically (using OOP).
    """
    class Sender(Agent):
        def on_init(self):
            self.count = 0
            self.bind('PUSH', 'push')

        def tick(self):
            self.send('push', self.count)
            self.count += 1

    sender = run_agent('sender', base=Sender)
    receiver = run_agent('receiver')
    receiver.connect(sender.addr('push'), handler=set_received)
    # Start timer
    sender.each(0.1, 'tick')
    time.sleep(2)
    assert abs(receiver.get_attr('received') - 20) <= 1


def test_timer_each_fall_behind(nsproxy):
    """
    Test a timer executed periodically and falling behind the period.

    If a sequence of events takes longer to run than the time available
    before the next event, the repeater will simply fall behind.
    """
    def tick(agent):
        agent.send('push', agent.count)
        time.sleep(.2)
        agent.count += 1

    sender = run_agent('sender')
    sender.set_attr(count=0)
    receiver = run_agent('receiver')
    addr = sender.bind('PUSH', alias='push')
    receiver.connect(addr, handler=set_received)
    # Start timer
    sender.each(0., tick)
    time.sleep(2.0)
    assert abs(receiver.get_attr('received') - 10) <= 1


def test_timer_each_stop_uuid(nsproxy):
    """
    Test a timer executed periodically and stopped by its UUID.
    """
    def tick(agent):
        agent.send('push', agent.count)
        agent.count += 1

    sender = run_agent('sender')
    receiver = run_agent('receiver')
    addr = sender.bind('PUSH', alias='push')
    receiver.connect(addr, handler=set_received)

    sender.set_attr(count=0)
    uuid = sender.each(0.1, tick)
    time.sleep(1)
    assert abs(receiver.get_attr('received') - 10) <= 1
    sender.stop_timer(uuid)
    time.sleep(1)
    assert abs(receiver.get_attr('received') - 10) <= 1
    assert uuid not in sender.list_timers()


def test_timer_each_stop_alias(nsproxy):
    """
    Test a timer executed periodically and stopped by an alias.
    """
    def tick(agent):
        agent.send('push', agent.count)
        agent.count += 1

    sender = run_agent('sender')
    receiver = run_agent('receiver')
    addr = sender.bind('PUSH', alias='push')
    receiver.connect(addr, handler=set_received)

    sender.set_attr(count=0)
    sender.each(0.1, tick, alias='aliased_timer')
    time.sleep(1)
    assert abs(receiver.get_attr('received') - 10) <= 1
    sender.stop_timer('aliased_timer')
    time.sleep(1)
    assert abs(receiver.get_attr('received') - 10) <= 1
    assert 'aliased_timer' not in sender.list_timers()


def test_stop_all_timers(nsproxy):
    """
    Calling `stop_all_timers()` should stop all currently running timers.
    """
    def tick(agent):
        agent.send('push', agent.count)
        agent.count += 1

    sender = run_agent('sender')
    receiver = run_agent('receiver')
    addr = sender.bind('PUSH', alias='push')
    receiver.connect(addr, handler=set_received)

    sender.set_attr(count=0)
    sender.each(0.1, tick, alias='timer0')
    sender.each(0.1, tick, alias='timer1')
    time.sleep(1)
    assert abs(receiver.get_attr('received') - 20) <= 1
    sender.stop_all_timers()
    time.sleep(1)
    assert abs(receiver.get_attr('received') - 20) <= 1
    assert len(sender.list_timers()) == 0


def test_timer_after(nsproxy):
    """
    Test a timer executed once after a time delay.
    """
    def event(agent, number):
        agent.count += number

    agent = run_agent('agent')
    agent.set_attr(count=0)
    # Start timer
    agent.after(1, event, 2)
    agent.after(2, event, 1)
    time.sleep(0.9)
    assert agent.get_attr('count') == 0
    time.sleep(0.2)
    assert agent.get_attr('count') == 2
    time.sleep(1)
    assert agent.get_attr('count') == 3


def test_timer_after_oop(nsproxy):
    """
    Test a timer executed once after a time delay (using OOP).
    """
    class Foo(Agent):
        def on_init(self):
            self.count = 0

        def event(self, number):
            self.count += number

        def setup_timer(self, delay, number):
            self.after(delay, 'event', number)

    agent = run_agent('agent', base=Foo)
    # Start timer
    agent.setup_timer(0.5, 1)
    agent.setup_timer(1.0, 2)
    time.sleep(0.6)
    assert agent.get_attr('count') == 1
    time.sleep(0.5)
    assert agent.get_attr('count') == 3


def test_timer_after_stop_uuid(nsproxy):
    """
    Test a timer executed once after a time delay and stopped by its UUID.
    """
    def event(agent, number):
        agent.count += number

    agent = run_agent('agent')
    agent.set_attr(count=0)
    # Start timer
    uuid = agent.after(1, event, 2)
    agent.stop_timer(uuid)
    time.sleep(1.1)
    assert agent.get_attr('count') == 0


def test_timer_after_stop_alias(nsproxy):
    """
    Test a timer executed once after a time delay and stopped by its alias.
    """
    def event(agent, number):
        agent.count += number

    agent = run_agent('agent')
    agent.set_attr(count=0)
    # Start timer
    agent.after(1, event, 2, alias='foo')
    agent.stop_timer('foo')
    time.sleep(1.1)
    assert agent.get_attr('count') == 0
