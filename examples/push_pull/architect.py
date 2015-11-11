from functions import print_message
from osbrain.core import Proxy


pusher = Proxy('Pusher')
puller = Proxy('Puller')

addr = pusher.bind('PUSH', alias='push')
puller.connect(addr, handler=print_message)

puller.run()
pusher.send('push', 'Hello, world!')
