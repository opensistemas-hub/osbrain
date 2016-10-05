from osbrain import run_nameserver
from osbrain import run_agent


if __name__ == '__main__':

    # System deployment
    run_nameserver()
    agent = run_agent('Example')

    # Log a message
    agent.log_info('Hello world!')
