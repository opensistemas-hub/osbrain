'''
A simple example in which the different serialization setting
options are shown.
'''
import osbrain
from osbrain import run_nameserver
from osbrain import run_agent


def set_received(agent, message, topic=None):
    print('Got a message: {}'.format(message))


if __name__ == '__main__':
    # We can define the default serializer through environment variables.
    # This will be the preferred method from now on, unless overriden.
    osbrain.config['SERIALIZER'] = 'pickle'

    ns = run_nameserver()

    a0 = run_agent('a0')
    # Agent a1 will ignore the default serialization and use the `raw` option
    # instead. By default, all of `a1` sockets will use `raw` option, unless
    # overriden.
    a1 = run_agent('a1', serializer='raw')
    # Bind a specific socket using json serialization, which will ignore both
    # the global configuration and the per-agent configuration.
    addr = a1.bind('PULL', handler=set_received, serializer='json')
    a0.connect(addr, 'push')
    message = b'Hello world'
    # An exception will be raised, since this very specific socket uses json
    # serialization, which is not capable of serializing raw bytes.
    try:
        a0.send('push', message)
    except:
        print('Something went wrong...')

    ns.shutdown()
