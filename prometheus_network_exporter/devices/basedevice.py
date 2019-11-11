
'''
    General Device
'''
import socket
import threading
from prometheus_client import CollectorRegistry


class Device():
    def __init__(self, hostname: str, device, **kwargs):
        self.hostname = hostname
        self.device = device
        self.lock = threading.Lock()
        self.exception_counter = kwargs.pop("exception_counter", None)
        self.types = kwargs.pop('types')
        self.registry = CollectorRegistry()

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

    def metrics(self, types):
        raise NotImplementedError
