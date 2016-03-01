from osbrain import random_nameserver
from osbrain import run_agent


def log_message(agent, message):
    agent.log_info('received: %s' % message)


def hello_world(agent):
    agent.log_info('Sending message...')
    agent.send('push', 'Hello, world!')


if __name__ == '__main__':

    # System deployment
    ns = random_nameserver()
    pusher = run_agent('Pusher', nsaddr=ns)
    puller = run_agent('Puller', nsaddr=ns)

    # System configuration
    addr = pusher.bind('PUSH', alias='push')
    pusher.set_method(iddle=hello_world)
    puller.connect(addr, handler=log_message)
