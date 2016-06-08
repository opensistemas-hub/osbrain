import random
from osbrain import random_nameserver
from osbrain import run_agent


def hello_world(agent):
    topic = random.choice(['a', 'b'])
    agent.log_info('Sending %s message...' % topic)
    agent.send('pub', 'Hello, world!', topic=topic)


def log_a(agent, message):
    agent.log_info('a: %s' % message)


def log_b(agent, message):
    agent.log_info('b: %s' % message)


if __name__ == '__main__':

    # System deployment
    ns = random_nameserver()
    publisher = run_agent('Publisher', nsaddr=ns)
    subscriber0 = run_agent('Subscriber0', nsaddr=ns)
    subscriber1 = run_agent('Subscriber1', nsaddr=ns)
    subscriber2 = run_agent('Subscriber2', nsaddr=ns)

    # System configuration
    addr = publisher.bind('PUB', alias='pub')
    publisher.set_method(iddle=hello_world)
    subscriber0.connect(addr, handler={'a': log_a, 'b': log_b})
    subscriber1.connect(addr, handler={'a': log_a})
    subscriber2.connect(addr, handler={'b': log_b})
