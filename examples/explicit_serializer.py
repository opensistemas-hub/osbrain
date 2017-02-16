import time

from osbrain import run_nameserver
from osbrain import run_agent


# Simple handler for example purposes
def set_received(agent, message, topic=None):
    agent.received = message


if __name__ == '__main__':
    # System deployment
    run_nameserver()
    a0 = run_agent('a0')
    a1 = run_agent('a1')

    # Bind to a socket, specifying the serializer type
    addr = a1.bind('PULL', handler=set_received, serializer='pickle')

    # Stablish a connection. Note that serializer is not needed, since it is
    # automatically chosen appropiately.
    a0.connect(addr, 'push')

    a0.send('push', 'Hello world')

    while not a1.get_attr('received'):
        time.sleep(0.1)
    print('Message received!')
