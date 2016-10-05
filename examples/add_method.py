from osbrain import run_agent
from osbrain import run_nameserver


def set_x(self, value):
    self.x = value


def set_y(self, value):
    self.y = value


def add_xy(self):
    return self.x + self.y


if __name__ == '__main__':

    # System deployment
    run_nameserver()
    agent = run_agent('Example')

    # System configuration
    agent.set_method(set_x, set_y, add=add_xy)

    # Trying the new methods
    agent.set_x(1)
    agent.set_y(2)
    print(agent.add())
