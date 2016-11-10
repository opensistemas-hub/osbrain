from osbrain.core import AgentProcess

from common import nsaddr  # pragma: no flakes


def test_agent_error_os(nsaddr):
    """
    Agent start() should raise an error if address is already in use.
    """
    agent = AgentProcess('a0', nsaddr, nsaddr)
    try:
        agent.start()
        assert 0
    except RuntimeError:
        pass
    except Exception:
        raise


def test_agent_error_permission(nsaddr):
    """
    Agent start() should raise an error if it has not sufficient permissions.
    """
    agent = AgentProcess('a0', nsaddr, '127.0.0.1:22')
    try:
        agent.start()
        assert 0
    except RuntimeError:
        pass
    except Exception:
        raise
