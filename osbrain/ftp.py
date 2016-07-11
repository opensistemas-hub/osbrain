"""
Implementation of FTP-related features.
"""
import Pyro4
from .core import BaseAgent
from .common import address_to_host_port


class FTPAgent(BaseAgent):
    """
    An agent that provides basic FTP functionality.
    """
    def ftp_configure(self, addr, user, passwd, path, perm='elr'):
        from pyftpdlib.authorizers import DummyAuthorizer
        from pyftpdlib.handlers import FTPHandler
        from pyftpdlib.servers import FTPServer
        # Create authorizer
        authorizer = DummyAuthorizer()
        authorizer.add_user(user, passwd, path, perm=perm)
        # Create handler
        handler = FTPHandler
        handler.authorizer = authorizer
        # Create server
        host, port = address_to_host_port(addr)
        if port is None:
            port = 0
        self.ftp_server = FTPServer((host, port), handler)
        return self.ftp_server.socket.getsockname()

    @Pyro4.oneway
    def ftp_run(self):
        # Serve forever
        self.ftp_server.serve_forever()

    def ftp_addr(self):
        return self.ftp_server.socket.getsockname()

    def ftp_retrieve(self, addr, origin, destiny, user, passwd):
        import ftplib
        host, port = addr
        ftp = ftplib.FTP()
        ftp.connect(host, port)
        ftp.login(user, passwd)
        ftp.retrbinary('RETR %s' % origin, open(destiny, 'wb').write)
        ftp.close()
        return destiny
