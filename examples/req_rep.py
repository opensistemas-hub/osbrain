from osbrain import run_agent
from osbrain import run_nameserver


def reply(agent, message):
    return 'Received ' + str(message)


if __name__ == '__main__':

    run_nameserver()
    alice = run_agent('Alice')
    bob = run_agent('Bob')

    addr = alice.bind('REP', alias='main', handler=reply)
    bob.connect(addr, alias='main')

    for i in range(10):
        bob.send('main', i)
        reply = bob.recv('main')
        print(reply)
