from osbrain import run_nameserver
from osbrain import run_agent


if __name__ == '__main__':

    # System deployment
    ns = run_nameserver()
    run_agent('Agent0', ns)
    run_agent('Agent1', ns)
    run_agent('Agent2', ns)

    # Create a proxy to Agent1 and log a message
    agent = ns.proxy('Agent1')
    agent.log_info('Hello world!')
