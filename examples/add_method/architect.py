from functions import add
from osbrain.core import Proxy


agent = Proxy('Blank')

agent.add_method(add)
x = agent.add(1, 2)

print(x)
