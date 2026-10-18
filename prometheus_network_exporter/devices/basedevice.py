"""
General Device
"""

import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from prometheus_client import CollectorRegistry

# Reverse lookups block on the resolver. A route reflector has hundreds of
# peers, so uncached addresses are resolved on a small pool instead of one
# after the other; names rarely change, an hour of caching is plenty.
DNS_TTL_SECONDS = 3600
_RESOLVER = ThreadPoolExecutor(max_workers=8, thread_name_prefix="dns")


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
        # Reverse DNS per address with its expiry. One dict per device and no
        # size limit, so the peers of a route reflector stay cached between
        # scrapes instead of evicting each other.
        self._names = {}
        self._names_lock = threading.Lock()
        self.dns_ttl = float(self.options.get("dns_ttl_seconds", DNS_TTL_SECONDS))

    def is_connected(self):
        raise NotImplementedError

    def clear_cache(self):
        with self._names_lock:
            self._names.clear()

    @property
    def cache_info(self):
        with self._names_lock:
            return {"entries": len(self._names)}

    def lookup(self, ip) -> str:
        if ip is None or ip == "None":
            return ""
        now = time.monotonic()
        with self._names_lock:
            hit = self._names.get(ip)
        if hit is not None and hit[0] > now:
            return hit[1]
        name = self._resolve(ip)
        with self._names_lock:
            self._names[ip] = (now + self.dns_ttl, name)
        return name

    @staticmethod
    def _resolve(ip) -> str:
        try:
            return socket.gethostbyaddr(ip)[0]
        except (OSError, UnicodeError):
            # herror, gaierror (resolver down, scoped link-local addresses)
            # and timeouts: a missing name must not cost the metrics.
            return ip

    def prefetch(self, addresses) -> None:
        """Resolve the addresses that are not cached yet, in parallel."""
        now = time.monotonic()
        with self._names_lock:
            pending = sorted(
                {
                    ip
                    for ip in addresses
                    if ip and ip != "None"
                    and (ip not in self._names or self._names[ip][0] <= now)
                }
            )
        if len(pending) > 1:
            # list() waits for all of them; lookup() stores every result.
            list(_RESOLVER.map(self.lookup, pending))

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
