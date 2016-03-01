from osbrain import random_nameserver
from osbrain import run_agent


def hello_world(agent):
    agent.log_info('Hello world!')


if __name__ == '__main__':

    # System deployment
    ns = random_nameserver()
    agent = run_agent('Agent0', nsaddr=ns)

    # System configuration
    agent.set_method(iddle=hello_world)
