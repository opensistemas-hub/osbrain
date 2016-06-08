import random
from osbrain import random_nameserver
from osbrain import run_agent


def log_message(agent, message):
    agent.log_info('received: %s' % message)


def hello_world(agent):
    agent.log_info('Sending message...')
    agent.send('pub', 'Hello, world!')


if __name__ == '__main__':

    # System deployment
    ns = random_nameserver()
    publisher = run_agent('Publisher', nsaddr=ns)
    subscriber = run_agent('Subscriber', nsaddr=ns)

    # System configuration
    addr = publisher.bind('PUB', alias='pub')
    publisher.set_method(iddle=hello_world)
    subscriber.connect(addr, handler=log_message)
