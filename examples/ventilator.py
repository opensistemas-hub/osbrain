import time
from osbrain import run_agent
from osbrain import run_nameserver


def heavy_processing(agent, message):
    agent.log_info('%s seconds task...' % message)
    time.sleep(message)
    agent.send('results', '%s finished with %s' % (agent.name, message))


if __name__ == '__main__':

    run_nameserver()

    results = run_agent('Results')
    results.bind('PULL', alias='results', handler=lambda a, m: a.log_info(m))

    ventilator = run_agent('Ventilator')
    ventilator_addr = ventilator.bind('PUSH', alias='push')

    for i in range(5):
        worker = run_agent('Worker%s' % i)
        worker.connect(results.addr('results'), alias='results')
        worker.connect(ventilator_addr, handler=heavy_processing)

    for task in [5, 1, 1, 1, 1, 5, 1, 1, 1, 1]:
        ventilator.send('push', task)
