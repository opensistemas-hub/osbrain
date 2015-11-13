import time


def loop(agent):
    for i in range(10):
        if not i % 5:
            agent.send('push', 5)
        else:
            agent.send('push', 1)


def print_received(self, message):
    try:
        t0 = self.t0
    except AttributeError as error:
        self.t0 = time.time()
        return
    t1 = time.time()
    print('[%02.0f since first] %s' % (t1 - t0, message))


def heavy_processing(self, message):
    time.sleep(message)
    self.send('results', message)
