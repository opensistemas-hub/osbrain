import time
from osbrain import run_agent
from osbrain import run_nameserver
from osbrain import Agent


class Greeter(Agent):
    def on_init(self):
        self.bind('PUSH', alias='main')

    def hello(self, name):
        self.send('main', 'Hello, %s!' % name)


class Bob(Agent):
    def custom_log(self, message):
        self.log_info('Received: %s' % message)


if __name__ == '__main__':

    # System deployment
    ns = run_nameserver()
    alice = run_agent('Alice', base=Greeter)
    bob = run_agent('Bob', base=Bob)

    # System configuration
    bob.connect(alice.addr('main'), handler='custom_log')

    # Send messages
    for _ in range(3):
        alice.hello('Bob')
        time.sleep(1)

    ns.shutdown()
