from functions import print_message
from functions import loop
from osbrain.core import Proxy


pusher = Proxy('Pusher')
puller = Proxy('Puller')

pusher.set_loop(loop)
addr = pusher.bind('PUSH', alias='push')
puller.connect(addr, handler=print_message)

puller.run()
pusher.run()
