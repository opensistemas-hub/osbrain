import time
from osbrain import random_nameserver
from osbrain import run_agent


def log(agent, message):
    agent.log_info(message)


def heavy_processing(agent, message):
    agent.log_info('%s seconds task...' % message)
    time.sleep(message)
    agent.send('results', '%s finished with %s' % (agent.name, message))


if __name__ == '__main__':

    ns = random_nameserver()

    results = run_agent('Results', nsaddr=ns)
    results_addr = results.bind('PULL', handler=log)

    ventilator = run_agent('Ventilator', nsaddr=ns)
    ventilator_addr = ventilator.bind('PUSH', alias='push')

    for i in range(5):
        worker = run_agent('Worker%s' % i, nsaddr=ns)
        worker.connect(results_addr, alias='results')
        worker.connect(ventilator_addr, handler=heavy_processing)

    # Send tasks
    for i in range(10):
        if not i % 5:
            ventilator.send('push', 5)
        else:
            ventilator.send('push', 1)
