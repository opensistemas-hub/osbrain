import time

from osbrain import run_agent
from osbrain import run_nameserver


def reply_late(agent, message):
    time.sleep(1)
    return 'Hello, Bob!'


def process_reply(agent, message):
    agent.log_info('Processed reply: %s' % message)


if __name__ == '__main__':

    ns = run_nameserver()
    alice = run_agent('Alice')
    bob = run_agent('Bob')

    addr = alice.bind('ASYNC_REP', handler=reply_late)
    bob.connect(addr, alias='alice', handler=process_reply)

    bob.send('alice', 'Hello, Alice!')
    bob.log_info('I am done!')

    bob.log_info('Waiting for Alice to reply...')
    time.sleep(2)

    ns.shutdown()
