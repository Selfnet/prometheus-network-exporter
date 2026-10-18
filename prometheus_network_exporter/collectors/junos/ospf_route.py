"""OSPF and OSPFv3 route metrics from ``show ospf route detail``.

Route counts are exported per area, path type, route type and next-hop
interface. This is where an unexpected path shows up: traffic for a set of
prefixes suddenly counted behind a different interface. Watched prefixes
additionally get their cost and next hop.
"""

from __future__ import annotations

import collections
from typing import Iterable

from prometheus_client.core import GaugeMetricFamily

from ..base import Collector
from . import base
from .rpcs import OSPF_PROTOCOLS
from .xmlutil import Reader, add, is_ipv6, iter_items, label, text

ENTRIES = ("ospf-route-entry", "ospf3-route-entry")
NEXTHOPS = ("ospf-next-hop", "ospf3-next-hop")
COUNT_LABELS = ["area", "path_type", "route_type", "nexthop_interface"]
COST_LABELS = ["prefix", "path_type", "nexthop_interface", "nexthop"]


class OSPFRouteCollector(Collector):
    def __init__(self, device, protocol: str = "ospf", watch: Iterable[str] = ()):
        if protocol not in OSPF_PROTOCOLS:
            raise ValueError(f"Unsupported OSPF protocol: {protocol}")
        self.protocol = protocol
        self.watch = [p for p in watch if is_ipv6(p) == (protocol == "ospf3")]
        super().__init__(f"{base}_{protocol}", device, config={})
        self.reader = Reader(device.schema, f"{protocol}_route")

    def collect(self):
        reply = self.device.rpc_reply(
            f"get_{self.protocol}_route_information", detail=True
        )
        if reply is None:
            return
        read = self.reader
        routes = GaugeMetricFamily(
            f"{self.base_name}_routes",
            "OSPF routes by type and next-hop interface; an ECMP route counts "
            "once per interface",
            labels=COUNT_LABELS,
        )
        cost = GaugeMetricFamily(
            f"{self.base_name}_route_cost",
            "Cost of a watched prefix per next hop",
            labels=COST_LABELS,
        )
        counts = collections.Counter()
        for entry in iter_items(reply, ENTRIES):
            prefix = read.text(entry, "address-prefix")
            path_type = label(read.text(entry, "route-path-type"))
            route_type = label(read.text(entry, "route-type"))
            area = label(read.text(entry, "ospf-area", required=False))
            route_cost = read.number(entry, "interface-cost")
            nexthops = [
                (
                    label(text(hop, "next-hop-name/interface-name")),
                    label(text(hop, "next-hop-address/interface-address")),
                )
                for hop in iter_items(entry, NEXTHOPS)
            ] or [("", "")]
            for interface in sorted({interface for interface, _ in nexthops}):
                counts[(area, path_type, route_type, interface)] += 1
            if prefix in self.watch:
                for interface, address in nexthops:
                    add(cost, [prefix, path_type, interface, address], route_cost)
        for key, count in sorted(counts.items()):
            routes.add_metric(list(key), float(count))
        yield from read.unique((routes, cost))
