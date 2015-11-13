from osbrain.core import Agent


Agent('Dispatcher').start()
for i in range(5):
    Agent('Worker%i' % i).start()
Agent('Results').start()
