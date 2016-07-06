import random
import pytest
from osbrain.nameserver import NameServer
from osbrain.address import SocketAddress


@pytest.yield_fixture(scope='function')
def nsaddr(request):
    while True:
        try:
            # Bind to random port
            host = '127.0.0.1'
            port = random.randrange(10000, 20000)
            addr = SocketAddress(host, port)
            nameserver = NameServer(addr)
            nameserver.start()
            break
        except RuntimeError:
            continue
        except:
            raise
    yield addr
    nameserver.shutdown()
