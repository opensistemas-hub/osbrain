from osbrain import Agent
from osbrain import NameServer

from common import nsaddr  # pragma: no flakes


def test_ns_error_os(nsaddr):
    """
    Name server start() should raise an error if address is already in use.
    """
    ns = NameServer(nsaddr)
    try:
        ns.start()
        ns.shutdown()
        assert 0
    except RuntimeError:
        pass
    except:
        raise


def test_ns_error_permission():
    """
    Name server start() should raise an error if it has not sufficient
    permissions.
    """
    ns = NameServer('127.0.0.1:22')
    try:
        ns.start()
        ns.shutdown()
        assert 0
    except RuntimeError:
        pass
    except:
        raise


def test_agent_error_os(nsaddr):
    """
    Agent start() should raise an error if address is already in use.
    """
    agent = Agent('a0', nsaddr, nsaddr)
    try:
        agent.start()
        agent.shutdown()
        assert 0
    except RuntimeError:
        pass
    except:
        raise


def test_agent_error_permission(nsaddr):
    """
    Agent start() should raise an error if it has not sufficient permissions.
    """
    agent = Agent('a0', nsaddr, '127.0.0.1:22')
    try:
        agent.start()
        agent.shutdown()
        assert 0
    except RuntimeError:
        pass
    except:
        raise
