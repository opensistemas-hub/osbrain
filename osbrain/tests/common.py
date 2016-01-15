import pytest
import random
from Pyro4.errors import NamingError
from osbrain.core import NameServer
from osbrain.core import SocketAddress


@pytest.fixture(scope='function')
def nsaddr(request):
    while True:
        try:
            # Bind to random port
            host = '127.0.0.1'
            port = random.randrange(10000, 20000)
            addr = SocketAddress(host, port)
            ns = NameServer(addr)
            def terminate():
                ns.shutdown()
            request.addfinalizer(terminate)
            ns.start()
            return addr
        except NamingError:
            continue
        except PermissionError:
            continue
        except:
            raise
