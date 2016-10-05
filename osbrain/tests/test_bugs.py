"""
Test file for bugs found in osbrain.
"""
import sys
import time

from osbrain.core import run_agent

from common import nsproxy  # pragma: no flakes


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
    while True:
        count = agent.get_attr('count')
        if count > sys.getrecursionlimit():
            return
        time.sleep(0.1)
        if count == agent.get_attr('count'):
            raise RuntimeError('Probable recursion level exceeded!')
