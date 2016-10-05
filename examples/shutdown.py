import time

from osbrain import run_agent
from osbrain import run_nameserver


def tick(agent):
    agent.log_info('tick')


if __name__ == '__main__':

    ns = run_nameserver()
    a0 = run_agent('Agent0')
    a1 = run_agent('Agent1')

    a0.each(1, tick)
    a1.each(1, tick)
    time.sleep(3)

    a0.shutdown()
    time.sleep(3)

    ns.shutdown()
