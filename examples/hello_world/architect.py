from osbrain.core import Proxy


p0 = Proxy('agent0')
p1 = Proxy('agent1')

p0.log_info('Hello...')
p1.log_info('World!')
