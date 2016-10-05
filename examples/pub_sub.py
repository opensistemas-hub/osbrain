import time
from osbrain import run_agent
from osbrain import run_nameserver


def log_message(agent, message):
    agent.log_info('Received: %s' % message)


if __name__ == '__main__':

    # System deployment
    run_nameserver()
    alice = run_agent('Alice')
    bob = run_agent('Bob')
    eve = run_agent('Eve')

    # System configuration
    addr = alice.bind('PUB', alias='main')
    bob.connect(addr, handler=log_message)
    eve.connect(addr, handler=log_message)

    # Send messages
    while True:
        time.sleep(1)
        alice.send('main', 'Hello, all!')
