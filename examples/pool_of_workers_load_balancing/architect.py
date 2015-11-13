from functions import rep_handler
from functions import print_received
from functions import worker_loop
from osbrain.core import Proxy


dispatcher = Proxy('Dispatcher')
dispatcher.set_attr('i', 0)
dispatcher_addr = dispatcher.bind('REP', alias='rep', handler=rep_handler)
dispatcher.run()

results = Proxy('Results')
results_addr = results.bind('PULL', handler=print_received)
results.run()

for i in range(5):
    worker = Proxy('Worker%s' % i)
    worker.connect(results_addr, alias='results')
    worker.connect(dispatcher_addr, alias='dispatcher')
    worker.set_loop(worker_loop)
    worker.run()
