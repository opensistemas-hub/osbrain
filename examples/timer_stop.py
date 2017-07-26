import time
from osbrain import run_agent
from osbrain import run_nameserver


def delayed(agent, message):
    agent.log_info(message)


if __name__ == '__main__':

    ns = run_nameserver()
    agent = run_agent('a0')

    agent.after(1, delayed, 'Hello!')
    # Timer ID returned
    timer0 = agent.after(1, delayed, 'Never logged')
    # Timer alias set
    agent.after(1, delayed, 'Never logged either', alias='timer_alias')

    # Stop timers by ID and alias
    agent.stop_timer(timer0)
    agent.stop_timer('timer_alias')

    time.sleep(2)

    ns.shutdown()
