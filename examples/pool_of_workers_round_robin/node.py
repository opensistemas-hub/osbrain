from osbrain.core import Agent


Agent('Ventilator').start()
for i in range(5):
    Agent('Worker%i' % i).start()
Agent('Results').start()
