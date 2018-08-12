
'''
    General Device 
'''
import socket

class NetworkDevice():
    def __init__(self, device):
        self.device = device

    def is_connected(self):
        pass

    def lookup(self, ip):
        try:
            return socket.gethostbyaddr(ip)[0]
        except (socket.herror):
            return ip

    def get_bgp(self):
        raise NotImplementedError

    def get_interface(self, interface_names=None, ospf=False, optics=False):
        raise NotImplementedError

    def get_environment(self):
        raise NotImplementedError

    def get_ospf(self, interface_names=None):
        raise NotImplementedError

    def get_optics(self, interface_names=None):
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def reconnect(self):
        self.disconnect()
        return self.connect()
