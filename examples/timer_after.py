from osbrain import run_agent
from osbrain import run_nameserver


def delayed(agent):
    agent.log_info('Logged later')


if __name__ == '__main__':

    run_nameserver()
    agent = run_agent('a0')

    agent.after(1, delayed)
    agent.log_info('Logged now')
