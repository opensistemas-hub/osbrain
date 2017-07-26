import time
from osbrain import run_agent
from osbrain import run_nameserver


def heavy_processing(agent, message):
    agent.log_info('%s seconds task...' % message)
    time.sleep(message)
    agent.send('results', '%s finished with %s' % (agent.name, message))


def append_received(agent, message):
    agent.log_info(message)
    agent.received.append(message)

if __name__ == '__main__':

    ns = run_nameserver()

    results = run_agent('Results')
    results.set_attr(received=[])
    results.bind('PULL', alias='results', handler=append_received)

    ventilator = run_agent('Ventilator')
    ventilator_addr = ventilator.bind('PUSH', alias='push')

    for i in range(5):
        worker = run_agent('Worker%s' % i)
        worker.connect(results.addr('results'), alias='results')
        worker.connect(ventilator_addr, handler=heavy_processing)

    for task in [5, 1, 1, 1, 1, 5, 1, 1, 1, 1]:
        ventilator.send('push', task)

    while len(results.get_attr('received')) != 10:
        time.sleep(0.1)

    ns.shutdown()
