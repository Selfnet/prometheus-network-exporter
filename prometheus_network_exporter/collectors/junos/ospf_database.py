"""OSPF and OSPFv3 link-state database metrics from ``show ospf database``.

Only aggregates are exported: LSA counts per area and type, the youngest LSA
age and the sequence number of our own router LSA. Note that Junos refreshes
every LSA about every 30 minutes, so a young LSA alone is not a topology
change; a jump in the own router LSA sequence number or in LSA counts is.
"""

from __future__ import annotations

import collections

from prometheus_client.core import GaugeMetricFamily

from ..base import Collector
from . import base
from .rpcs import OSPF_PROTOCOLS
from .xmlutil import Reader, add, find, label, localname, text

HEADERS = (
    "ospf-area-header",
    "ospf3-area-header",
    "ospf-intf-header",
    "ospf3-intf-header",
)
ENTRIES = ("ospf-database", "ospf3-database")
EXTERNAL_SCOPE = "external"


class OSPFDatabaseCollector(Collector):
    def __init__(self, device, protocol: str = "ospf"):
        if protocol not in OSPF_PROTOCOLS:
            raise ValueError(f"Unsupported OSPF protocol: {protocol}")
        self.protocol = protocol
        super().__init__(f"{base}_{protocol}_database", device, config={})
        self.reader = Reader(device.schema, f"{protocol}_database")

    def collect(self):
        reply = self.device.rpc_reply(f"get_{self.protocol}_database_information")
        if reply is None:
            return
        read = self.reader

        counts = collections.Counter()
        own = collections.Counter()
        youngest = {}
        own_router = {}
        area = ""
        # Area and interface headers precede the entries they apply to.
        for element in reply.iter():
            if not isinstance(element.tag, str):
                continue
            name = localname(element)
            if name in HEADERS:
                header_area = text(element, "ospf-area")
                if header_area is not None:
                    area = header_area
            elif name in ENTRIES:
                lsa_type = label(read.text(element, "lsa-type"))
                scope = EXTERNAL_SCOPE if lsa_type.lower() == "extern" else area
                key = (scope, lsa_type)
                counts[key] += 1
                own[key] += 0
                age = read.number(element, "age")
                if age is not None:
                    youngest[key] = min(youngest.get(key, age), age)
                if find(element, "our-entry") is not None:
                    own[key] += 1
                    if lsa_type.lower() == "router":
                        own_router[scope] = (
                            read.number(element, "sequence-number"),
                            age,
                        )

        labels = ["area", "lsa_type"]
        lsas = GaugeMetricFamily(
            f"{self.base_name}_lsas", "LSAs in the database", labels=labels
        )
        own_lsas = GaugeMetricFamily(
            f"{self.base_name}_own_lsas", "LSAs originated by this router", labels=labels
        )
        age_min = GaugeMetricFamily(
            f"{self.base_name}_lsa_age_seconds_min",
            "Age of the youngest LSA; LSAs are refreshed about every 30 minutes",
            labels=labels,
        )
        for key, count in sorted(counts.items()):
            lsas.add_metric(list(key), float(count))
            own_lsas.add_metric(list(key), float(own[key]))
            add(age_min, list(key), youngest.get(key))
        yield from read.unique((lsas, own_lsas, age_min))

        sequence = GaugeMetricFamily(
            f"{self.base_name}_own_router_lsa_sequence",
            "Sequence number of our router LSA; increments on every re-origination",
            labels=["area"],
        )
        router_age = GaugeMetricFamily(
            f"{self.base_name}_own_router_lsa_age_seconds",
            "Age of our router LSA",
            labels=["area"],
        )
        for scope, (value, age) in sorted(own_router.items()):
            add(sequence, [scope], value)
            add(router_age, [scope], age)
        yield from read.unique((sequence, router_age))
