"""
This example is relatively complex.

We will be creating a system in which agents will connect to different
name servers. Each name server will therefore represent a 'group' of agents.
That way, we can easily shut down all agents belonging to a group, without
interfering with the others.
"""
import time

from osbrain import run_agent
from osbrain import run_nameserver


def annoy(agent, message):
    agent.send('annoy', message)


def log_message(agent, message):
    agent.log_info('Received: %s' % message)


if __name__ == '__main__':

    ns = run_nameserver()
    ns_annoy = run_nameserver()

    # Create normal PUB/SUB communication
    listener = run_agent('listener', nsaddr=ns.addr())
    addr = listener.bind('SUB', alias='sub', handler=log_message)

    speaker = run_agent('speaker', nsaddr=ns.addr())
    speaker.connect(addr, alias='annoy')
    speaker.each(0.2, annoy, 'Blah blah...')

    # Create annoying agents registered in another name server
    annoyer_apple = run_agent('annoyer0', nsaddr=ns_annoy.addr())
    annoyer_apple.connect(addr, alias='annoy')
    annoyer_apple.each(0.2, annoy, 'apple')

    annoyer_grape = run_agent('annoyer1', nsaddr=ns_annoy.addr())
    annoyer_grape.connect(addr, alias='annoy')
    annoyer_grape.each(0.2, annoy, 'grape')

    time.sleep(1)
    # Shutting down the annoying agents through their name server
    ns_annoy.shutdown()

    time.sleep(1)
    ns.shutdown()
