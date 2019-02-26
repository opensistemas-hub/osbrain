import time

from osbrain import run_agent
from osbrain import run_nameserver


def log_a(agent, message):
    agent.log_info('Log a: %s' % message)


def log_b(agent, message):
    agent.log_info('Log b: %s' % message)


def send_messages(agent):
    agent.send('main', 'Apple', topic='a')
    agent.send('main', 'Banana', topic='b')


if __name__ == '__main__':

    # System deployment
    ns = run_nameserver()
    alice = run_agent('Alice')
    bob = run_agent('Bob')

    # System configuration
    addr = alice.bind('PUB', alias='main')
    alice.each(0.5, send_messages)
    bob.connect(addr, alias='listener', handler={'a': log_a})

    time.sleep(2)

    bob.unsubscribe('listener', 'a')
    bob.subscribe('listener', handler={'b': log_b})

    time.sleep(2)

    ns.shutdown()
