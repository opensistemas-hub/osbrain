import time


def loop(agent):
    for i in range(13):
        agent.send('push', i)


def print_received(self, message):
    print(message)


def heavy_processing(self, message):
    time.sleep(2)
    self.send('results', message * 2)
