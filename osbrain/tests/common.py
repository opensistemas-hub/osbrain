import random
import pytest
from Pyro4.errors import NamingError
from osbrain.nameserver import NameServer
from osbrain.address import SocketAddress


@pytest.fixture(scope='function')
def nsaddr(request):
    while True:
        try:
            # Bind to random port
            host = '127.0.0.1'
            port = random.randrange(10000, 20000)
            addr = SocketAddress(host, port)
            nameserver = NameServer(addr)
            def terminate():
                nameserver.shutdown()
            request.addfinalizer(terminate)
            nameserver.start()
            return addr
        except NamingError:
            continue
        except PermissionError:
            continue
        except:
            raise
