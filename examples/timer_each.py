import time
from osbrain import run_agent
from osbrain import run_nameserver


def log_message(agent, message):
    agent.log_info('Received: %s' % message)


def annoy(agent, say, more=None):
    message = say if not more else say + ' ' + more + '!'
    agent.send('annoy', message)


if __name__ == '__main__':

    ns = run_nameserver()
    orange = run_agent('Orange')
    apple = run_agent('Apple')
    addr = orange.bind('PUSH', alias='annoy')
    apple.connect(addr, handler=log_message)

    # Multiple timers with parameters
    orange.each(1.0, annoy, 'Hey')
    orange.each(1.4142, annoy, 'Apple')
    orange.each(3.1415, annoy, 'Hey', more='Apple')

    time.sleep(10)

    ns.shutdown()
