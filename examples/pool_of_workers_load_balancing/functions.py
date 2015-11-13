import time


def rep_handler(agent, message):
    if agent.i < 10:
        if not agent.i % 5:
            agent.send('rep', 5)
        else:
            agent.send('rep', 1)
    else:
        agent.send('rep', None)
    agent.i += 1


def print_received(agent, message):
    try:
        t0 = agent.t0
    except AttributeError as error:
        agent.t0 = time.time()
        return
    t1 = time.time()
    print('[%02.0f since first] %s' % (t1 - t0, message))


def worker_loop(agent):
    while True:
        agent.send('dispatcher', 'READY!')
        x = agent.recv('dispatcher')
        if x is None:
            break
        time.sleep(x)
        agent.send('results', x)
