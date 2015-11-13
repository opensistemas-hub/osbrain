from functions import loop
from functions import print_received
from functions import heavy_processing
from osbrain.core import Proxy


results = Proxy('Results')
results_addr = results.bind('PULL', handler=print_received)
ventilator = Proxy('Ventilator')
ventilator_addr = ventilator.bind('PUSH', alias='push')
ventilator.set_loop(loop)

for i in range(5):
    worker = Proxy('Worker%s' % i)
    worker.connect(results_addr, alias='results')
    worker.connect(ventilator_addr, handler=heavy_processing)
    worker.run()

results.run()
ventilator.run()
