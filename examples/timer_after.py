import time
from osbrain import run_agent
from osbrain import run_nameserver


def delayed(agent):
    agent.log_info('Logged later')


if __name__ == '__main__':

    ns = run_nameserver()
    agent = run_agent('a0')

    agent.after(2, delayed)
    agent.log_info('Logged now')

    time.sleep(2.5)

    ns.shutdown()
