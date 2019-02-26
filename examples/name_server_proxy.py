from osbrain import run_agent
from osbrain import run_nameserver

if __name__ == '__main__':

    # System deployment
    ns = run_nameserver()
    run_agent('Agent0')
    run_agent('Agent1')
    run_agent('Agent2')

    # Create a proxy to Agent1 and log a message
    agent = ns.proxy('Agent1')
    agent.log_info('Hello world!')

    ns.shutdown()
