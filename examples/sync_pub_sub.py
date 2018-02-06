import time

from osbrain import run_agent
from osbrain import run_nameserver


def publish(agent):
    agent.send('publisher', 'Publication...')


def reply_back(agent, message):
    return 'Received %s' % message


def read_subscription(agent, message):
    agent.log_info('Read: "%s"' % message)


def process_reply(agent, message):
    agent.log_info('Publisher replied with: "%s"' % message)


if __name__ == '__main__':

    ns = run_nameserver()
    publisher = run_agent('Publisher')
    client_a = run_agent('Client-A')
    client_b = run_agent('Client-B')

    addr = publisher.bind('SYNC_PUB', alias='publisher', handler=reply_back)
    client_a.connect(addr, alias='publisher', handler=read_subscription)
    client_b.connect(addr, alias='publisher', handler=read_subscription)

    publisher.each(0.1, publish)
    time.sleep(1)
    client_a.send('publisher', 'Request from A!', handler=process_reply)
    time.sleep(1)

    ns.shutdown()
