'''
Simple example that will demonstrate how to set the serializer at per socket
level.

Note that a crash is intended, since json does not support byte serialization.
'''
from osbrain import run_nameserver
from osbrain import run_agent


def set_received(agent, message, topic=None):
    print('Got a message: {}'.format(message))


if __name__ == '__main__':
    ns = run_nameserver()

    a0 = run_agent('a0')
    a1 = run_agent('a1')
    addr = a1.bind('PULL', handler=set_received, serializer='json')
    a0.connect(addr, 'push')
    message = b'Hello world'
    try:
        a0.send('push', message)
    except:
        print('Something went wrong...')

    ns.shutdown()
