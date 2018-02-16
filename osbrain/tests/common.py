import sys
import pytest
from pytest import mark

from osbrain import run_agent
from osbrain import run_logger
from osbrain import run_nameserver
from osbrain.helper import sync_agent_logger

skip_windows = mark.skipif(sys.platform == 'win32',
                           reason='Not supported on windows')
skip_windows_port_reuse = mark.skipif(sys.platform == 'win32',
                                      reason='Windows allows port reuse')
skip_windows_any_port = mark.skipif(sys.platform == 'win32',
                                    reason='Windows allows binding to well '
                                    'known ports')
skip_windows_spawn = mark.skipif(sys.platform == 'win32',
                                 reason='Windows does not support fork')
skip_windows_ipc = mark.skipif(sys.platform == 'win32',
                               reason='Windows does not support IPC')


def append_received(agent, message, topic=None):
    agent.received.append(message)


def set_received(agent, message, topic=None):
    agent.received = message


@pytest.fixture(scope='function')
def nsproxy(request):
    ns = run_nameserver()
    yield ns
    ns.shutdown()


@pytest.fixture(scope='function')
def agent_logger(request):
    ns = run_nameserver()
    agent = run_agent('a0')
    logger = run_logger('logger')
    agent.set_logger(logger)
    sync_agent_logger(agent=agent, logger=logger)
    yield agent, logger
    ns.shutdown()
