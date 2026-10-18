"""
General Device
"""

import socket
import threading

from ..utitlities import timed_cache
from prometheus_client import CollectorRegistry


class Device:
    def __init__(self, hostname: str, device, **kwargs):
        self.hostname = hostname
        self.device = device
        self.lock = threading.Lock()
        self.exception_counter = kwargs.pop("exception_counter", None)
        self.types = kwargs.pop("types")
        # Free-form per module options, e.g. the "routing" block of the config.
        self.options = kwargs.pop("options", None) or {}
        self.registry = CollectorRegistry()

    def is_connected(self):
        raise NotImplementedError

    def clear_cache(self):
        self.lookup.cache_clear()

    @property
    def cache_info(self):
        return self.lookup.cache_info()

    # cache two times as long as the dns default ttl
    @timed_cache(seconds=600)
    def lookup(self, ip) -> str:
        if ip is None or ip == "None":
            return ""
        try:
            return socket.gethostbyaddr(ip)[0]
        except (OSError, UnicodeError):
            # herror, gaierror (resolver down, scoped link-local addresses)
            # and timeouts: a missing name must not cost the metrics.
            return ip

    def register_collectors(self, types: list):
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def reconnect(self):
        self.disconnect()
        return self.connect()

    def collect(self):
        raise NotImplementedError
