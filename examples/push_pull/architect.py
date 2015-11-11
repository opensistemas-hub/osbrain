from functions import print_message
from osbrain.core import Proxy


pusher = Proxy('Pusher')
puller = Proxy('Puller')

addr = pusher.bind('push')
puller.connect(addr, print_message)

puller.run()
pusher.send(addr, 'Hello world!')
