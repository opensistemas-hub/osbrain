from osbrain import Agent
from osbrain import NameServer

from common import nsaddr


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


def test_ns_error_permission(nsaddr):
    """
    Name server start() should raise an error if it has not sufficient
    permissions.
    """
    # TODO: is there anything more reliable than trying port 22?
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
    # TODO: is there anything more reliable than trying port 22?
    agent = Agent('a0', nsaddr, '127.0.0.1:22')
    try:
        agent.start()
        agent.shutdown()
        assert 0
    except RuntimeError:
        pass
    except:
        raise

# TODO:
#  - Test "obscure" errors (exceptions not correctly returned by Pyro? or
#    not correctly propagated to the parent process?)
