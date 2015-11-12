import time


def print_message(agent, message):
    print('%s received: %s' % (agent.name, message))


def loop(agent):
    for i in range(3):
        agent.send('push', 'Hello, world!')
        time.sleep(1)
