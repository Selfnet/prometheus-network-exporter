
'''
    General Device 
'''
import socket

class Device():
    def __init__(self, hostname, device):
        self.hostname = hostname
        self.device = device

    def is_connected(self):
        raise NotImplementedError

    def lookup(self, ip):
        try:
            return socket.gethostbyaddr(ip)[0]
        except (socket.herror):
            return ip

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def reconnect(self):
        self.disconnect()
        return self.connect()

class Metrics(object):
    def metrics(self, types, dev, registry):
        raise NotImplementedError