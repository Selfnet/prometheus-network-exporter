"""Refresh optical RPC replies independently of the Prometheus scrape interval."""

import time

OPTICAL_RPCS = {
    "get_interface_optics_diagnostics_information",
    "get_chassis_inventory",
    "get_pic_detail",
}


class OpticsCache:
    def __init__(self, interval=300):
        self.interval = interval
        self.entries = {}

    def reply(self, rpc, args, fetch):
        if rpc not in OPTICAL_RPCS or self.interval == 0:
            return fetch(rpc, **args)
        now = time.monotonic()
        # Also discard entries for PICs or interface selections no longer used.
        self.entries = {key: value for key, value in self.entries.items()
                        if now - value[0] < self.interval}
        key = (rpc, tuple(sorted(args.items())))
        cached = self.entries.get(key)
        if cached is not None:
            return cached[2]
        # Expired values are already removed. A failed refresh must not serve
        # old measurements as though the optical query had succeeded.
        result = fetch(rpc, **args)
        if result is not None:
            self.entries[key] = (time.monotonic(), time.time(), result)
        return result
