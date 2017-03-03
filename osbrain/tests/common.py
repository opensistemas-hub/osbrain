import time
from uuid import uuid4

import pytest
from osbrain import run_nameserver


def logger_received(logger, log_name, message, timeout=1.):
    t0 = time.time()
    while True:
        time.sleep(0.01)
        log_history = logger.get_attr(log_name)
        if len(log_history) and message in log_history[-1]:
            break
        if timeout and time.time() - t0 > timeout:
            return False
    return True


def sync_agent_logger(agent, logger):
    while not len(logger.get_attr('log_history_info')):
        message = str(uuid4())
        agent.log_info(message)
        time.sleep(0.01)
    while message not in logger.get_attr('log_history_info')[-1]:
        time.sleep(0.01)


def agent_dies(agent, nsproxy, timeout=1.):
    t0 = time.time()
    while True:
        time.sleep(0.01)
        if agent not in nsproxy.agents():
            break
        if timeout and time.time() - t0 > timeout:
            return False
    return True


@pytest.fixture(scope='function')
def nsaddr(request):
    ns = run_nameserver()
    yield ns.addr()
    ns.shutdown()


@pytest.fixture(scope='function')
def nsproxy(request):
    ns = run_nameserver()
    yield ns
    ns.shutdown()
