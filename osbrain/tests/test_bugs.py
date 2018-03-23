"""
Test file for bugs found in osbrain.
"""
import sys

from osbrain import run_agent
from osbrain.helper import wait_agent_condition

from common import nsproxy  # noqa: F401


def test_timer_recursion(nsproxy):
    """
    This bug occured with the first implementation of the timer. After
    some iterations the timer would throw an exception when the recursion
    limit was exceeded. Timers should never reach a recursion limit.
    """
    def inc(agent):
        agent.count += 1

    agent = run_agent('a0')
    agent.set_attr(count=0)
    agent.each(0.0, inc)

    limit = sys.getrecursionlimit()
    assert wait_agent_condition(agent, lambda agent: agent.count > limit,
                                timeout=10)
