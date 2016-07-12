from osbrain import run_nameserver
from osbrain import run_agent


if __name__ == '__main__':

    # System deployment
    ns = run_nameserver()
    agent = run_agent('Agent0', ns)

    # Log a message
    agent.log_info('Hello world!')
