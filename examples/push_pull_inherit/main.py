import time
from osbrain import run_agent
from osbrain import run_nameserver
from osbrain import BaseAgent


class Greeter(BaseAgent):
    def on_init(self):
        self.bind('PUSH', alias='main')

    def hello(self, name):
        self.send('main', 'Hello, %s!' % name)


def log_message(agent, message):
    agent.log_info('Received: %s' % message)


if __name__ == '__main__':

    # System deployment
    ns = run_nameserver()
    alice = run_agent('Alice', ns, base=Greeter)
    bob = run_agent('Bob', ns)

    # System configuration
    bob.connect(alice.addr('main'), handler=log_message)

    # Send messages
    while True:
        time.sleep(1)
        alice.hello('Bob')
