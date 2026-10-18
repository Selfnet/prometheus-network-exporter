"""OSPF and OSPFv3 instance metrics from ``show ospf overview``.

The full SPF counter is the single best indicator for topology churn: its
rate stays visible however long the Prometheus scrape interval is.
"""

from __future__ import annotations

from prometheus_client.core import (
    CounterMetricFamily,
    GaugeMetricFamily,
    InfoMetricFamily,
)

from ..base import Collector
from . import base
from .rpcs import OSPF_PROTOCOLS
from .xmlutil import Reader, add, findall, label

TOPOLOGY_GAUGES = (
    ("spf_delay_seconds", "ospf-spf-delay", "Configured SPF delay"),
    ("spf_holddown_seconds", "ospf-spf-holddown", "Configured SPF holddown"),
    ("spf_rapid_runs", "ospf-spf-rapid-runs", "Configured rapid SPF runs"),
    ("exported_prefixes", "ospf-prefix-export-count", "Prefixes exported into OSPF"),
)


class OSPFOverviewCollector(Collector):
    def __init__(self, device, protocol: str = "ospf"):
        if protocol not in OSPF_PROTOCOLS:
            raise ValueError(f"Unsupported OSPF protocol: {protocol}")
        self.protocol = protocol
        super().__init__(f"{base}_{protocol}", device, config={})
        self.reader = Reader(device.schema, f"{protocol}_overview")

    def collect(self):
        reply = self.device.rpc_reply(f"get_{self.protocol}_overview_information")
        if reply is None:
            return
        read = self.reader

        info = InfoMetricFamily(self.base_name, "OSPF instance information")
        info.add_metric(
            [], {"router_id": label(read.text(reply, ".//ospf-router-id"))}
        )
        yield info

        spf_runs = CounterMetricFamily(
            f"{self.base_name}_full_spf_runs",
            "Full SPF runs since the protocol started",
            labels=["topology"],
        )
        gauges = {
            suffix: GaugeMetricFamily(
                f"{self.base_name}_{suffix}", doc, labels=["topology"]
            )
            for suffix, _, doc in TOPOLOGY_GAUGES
        }
        for topology in findall(reply, ".//ospf-topology-overview"):
            labels = [
                label(read.text(topology, "ospf-topology-name", required=False))
                or "default"
            ]
            add(spf_runs, labels, read.number(topology, "ospf-full-spf-count"))
            for suffix, field, _ in TOPOLOGY_GAUGES:
                add(gauges[suffix], labels, read.number(topology, field))
        yield spf_runs
        yield from gauges.values()

        neighbors_up = GaugeMetricFamily(
            f"{self.base_name}_area_neighbors_up",
            "Neighbours in state Full in the area",
            labels=["area"],
        )
        abrs = GaugeMetricFamily(
            f"{self.base_name}_area_abrs", "Area border routers in the area", labels=["area"]
        )
        asbrs = GaugeMetricFamily(
            f"{self.base_name}_area_asbrs",
            "AS boundary routers in the area",
            labels=["area"],
        )
        area_info = InfoMetricFamily(
            f"{self.base_name}_area", "OSPF area configuration", labels=["area"]
        )
        for area in findall(reply, ".//ospf-area-overview"):
            labels = [label(read.text(area, "ospf-area"))]
            add(
                neighbors_up,
                labels,
                read.number(area, "ospf-nbr-overview/ospf-nbr-up-count"),
            )
            add(abrs, labels, read.number(area, "ospf-abr-count"))
            add(asbrs, labels, read.number(area, "ospf-asbr-count"))
            area_info.add_metric(
                labels,
                {
                    "stub_type": label(read.text(area, "ospf-stub-type", required=False)),
                    "authentication": label(
                        read.text(area, "authentication-type", required=False)
                    ),
                },
            )
        yield from (neighbors_up, abrs, asbrs, area_info)
