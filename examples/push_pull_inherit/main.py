from osbrain import random_nameserver
from osbrain import run_agent
from osbrain import BaseAgent


class Push(BaseAgent):
    def on_init(self):
        self.bind('PUSH', alias='push')

    def iddle(self):
        self.log_info('Sending message...')
        self.send('push', 'Hello, world!')

def log_message(agent, message):
    agent.log_info('received: %s' % message)


if __name__ == '__main__':

    # System deployment
    ns = random_nameserver()
    pusher = run_agent('Pusher', nsaddr=ns, base=Push)
    puller = run_agent('Puller', nsaddr=ns)

    # System configuration
    puller.connect(pusher.addr('push'), handler=log_message)
