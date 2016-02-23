from osbrain import random_nameserver
from osbrain import run_agent


def log_message(agent, message):
    agent.log_info('received: %s' % message)


def iddle(agent):
    agent.send('push', 'Hello, world!')


if __name__ == '__main__':

    # System deployment
    ns = random_nameserver()
    pusher = run_agent('Pusher', nsaddr=ns)
    puller = run_agent('Pusher', nsaddr=ns)

    # System configuration
    addr = pusher.bind('PUSH', alias='push')
    pusher.set_method(iddle)
    puller.connect(addr, handler=log_message)
