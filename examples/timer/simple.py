from osbrain import run_agent
from osbrain import run_nameserver


def log_message(agent, message):
    agent.log_info('Received: %s' % message)


def greet_bob(agent):
    agent.send('main', 'Hello, Bob!')


if __name__ == '__main__':

    run_nameserver()
    alice = run_agent('Alice')
    bob = run_agent('Bob')
    addr = alice.bind('PUSH', alias='main')
    bob.connect(addr, handler=log_message)

    # Greet Bob each second
    alice.timer(greet_bob, each=1.)
