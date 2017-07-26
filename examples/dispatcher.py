import time
from osbrain import run_agent
from osbrain import run_nameserver


def rep_handler(agent, message):
    if not agent.tasks:
        return None
    return agent.tasks.pop()


def request_work(agent):
    x = agent.send_recv('dispatcher', 'READY!')
    if not x:
        agent.shutdown()
        return
    time.sleep(x)
    agent.send('results', '%s finished with %s' % (agent.name, x))


if __name__ == '__main__':

    ns = run_nameserver()

    results = run_agent('Results')
    results_addr = results.bind('PULL', handler=lambda x, y: x.log_info(y))

    dispatcher = run_agent('Dispatcher')
    dispatcher.set_attr(tasks=[1, 1, 1, 1, 5, 1, 1, 1, 1, 5])
    dispatcher_addr = dispatcher.bind('REP', alias='rep', handler=rep_handler)

    for i in range(5):
        worker = run_agent('Worker%s' % i)
        worker.connect(results_addr, alias='results')
        worker.connect(dispatcher_addr, alias='dispatcher')
        worker.each(0., request_work)

    while len(ns.agents()) > 2:
        time.sleep(0.1)

    ns.shutdown()
