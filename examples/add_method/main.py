from osbrain import random_nameserver
from osbrain import run_agent


def add(agent, x, y):
    return x + y


def log(agent):
    agent.log_info(agent.add(1, 2))


if __name__ == '__main__':

    # System deployment
    ns = random_nameserver()
    agent = run_agent('Blank', nsaddr=ns)

    # System configuration
    agent.set_method(add, iddle=log)
