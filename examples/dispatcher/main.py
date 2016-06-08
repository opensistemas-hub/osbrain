import time
from osbrain import random_nameserver
from osbrain import run_agent


def log(agent, message):
    agent.log_info(message)


def rep_handler(agent, message):
    if agent.i < 10:
        if not agent.i % 5:
            agent.send('rep', 5)
        else:
            agent.send('rep', 1)
    agent.i += 1


def worker_loop(agent):
    while True:
        agent.send('dispatcher', 'READY!')
        x = agent.recv('dispatcher')
        time.sleep(x)
        agent.send('results', '%s finished with %s' % (agent.name, x))


if __name__ == '__main__':

    ns = random_nameserver()

    results = run_agent('Results', nsaddr=ns)
    results_addr = results.bind('PULL', handler=log)

    dispatcher = run_agent('Dispatcher', nsaddr=ns)
    dispatcher.set_attr(i=0)
    dispatcher_addr = dispatcher.bind('REP', alias='rep', handler=rep_handler)

    for i in range(5):
        worker = run_agent('Worker%s' % i, nsaddr=ns)
        worker.connect(results_addr, alias='results')
        worker.connect(dispatcher_addr, alias='dispatcher')
        worker.stop()
        worker.set_loop(worker_loop)
        worker.run()
