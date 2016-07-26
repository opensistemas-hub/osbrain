from osbrain import run_nameserver
from osbrain import run_agent


if __name__ == '__main__':

    # System deployment
    ns = run_nameserver()
    run_agent('Agent0', ns)
    run_agent('Agent1', ns)
    run_agent('Agent2', ns)

    # Show agents registered in the name server
    for alias in ns.agents():
        print(alias)
