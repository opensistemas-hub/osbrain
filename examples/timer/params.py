from osbrain import run_agent
from osbrain import run_nameserver


def log_message(agent, message):
    agent.log_info('Received: %s' % message)


def greet(agent, say, more=None):
    message = say if not more else say + ' ' + more + '!'
    agent.send('annoy', message)


if __name__ == '__main__':

    run_nameserver()
    orange = run_agent('Orange')
    apple = run_agent('Apple')
    addr = orange.bind('PUSH', alias='annoy')
    apple.connect(addr, handler=log_message)

    # Multiple timers with parameters
    orange.timer(greet, each=1., args=('Hey', ))
    orange.timer(greet, each=1.4142, args=('Apple', ))
    orange.timer(greet, each=3.1415, args=('Hey', ), kwargs=dict(more='Apple'))
