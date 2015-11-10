from osbrain.core import Proxy


def handler(agent, message):
    print(message)


p0 = Proxy('agent0')
p1 = Proxy('agent1')

addr = p0.bind('push')
p1.connect(addr, handler)

p0.send(addr, 'Hello!')
