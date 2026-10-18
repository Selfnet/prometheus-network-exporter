"""Device level BGP metrics from ``show bgp summary`` and ``show bgp group``."""

from __future__ import annotations

import collections

from prometheus_client.core import GaugeMetricFamily

from ..base import Collector
from . import base
from .xmlutil import Reader, add, findall, iter_items, label

RIB_COUNTERS = (
    "total",
    "active",
    "received",
    "accepted",
    "suppressed",
    "history",
    "damped",
    "pending",
)


class BGPOverviewCollector(Collector):
    name = "bgp_overview"

    def __init__(self, device):
        super().__init__(f"{base}_bgp", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        summary = self.device.rpc_reply("get_bgp_summary_information")
        if summary is not None:
            yield from self.reader.unique(self._summary(summary))
        groups = self.device.rpc_reply("get_bgp_group_information")
        if groups is not None:
            yield from self.reader.unique(self._groups(groups))

    def _summary(self, summary):
        read = self.reader
        for suffix, field, doc in (
            ("peers", "peer-count", "Configured BGP peers"),
            ("peers_down", "down-peer-count", "BGP peers not in state Established"),
            ("groups", "group-count", "Configured BGP groups"),
        ):
            metric = GaugeMetricFamily(f"{self.base_name}_{suffix}", doc)
            add(metric, [], read.number(summary, field))
            yield metric

        ribs = {
            kind: GaugeMetricFamily(
                f"{self.base_name}_rib_{kind}_prefixes",
                f"Prefixes {kind} in the BGP RIB over all peers",
                labels=["rib"],
            )
            for kind in RIB_COUNTERS
        }
        # Only the direct children: every bgp-peer carries its own bgp-rib too.
        for table in findall(summary, "bgp-rib"):
            rib = label(read.text(table, "name"))
            for kind, metric in ribs.items():
                add(metric, [rib], read.number(table, f"{kind}-prefix-count"))
        yield from ribs.values()

    def _groups(self, reply):
        read = self.reader
        peers = GaugeMetricFamily(
            f"{self.base_name}_group_peers",
            "Peers configured in the BGP group",
            labels=["group", "type"],
        )
        established = GaugeMetricFamily(
            f"{self.base_name}_group_established_peers",
            "Peers of the BGP group in state Established",
            labels=["group", "type"],
        )
        # Junos splits one configured group into several entries (one per
        # option set, told apart by group-index); sum them per name and type.
        counts = collections.defaultdict(lambda: [None, None])
        for group in iter_items(reply, ("bgp-group",)):
            key = (
                label(read.text(group, "name")),
                label(read.first_text(group, ("type", "group-type"))),
            )
            for index, field in enumerate(("peer-count", "established-count")):
                value = read.number(group, field)
                if value is not None:
                    counts[key][index] = (counts[key][index] or 0.0) + value
        for key, (configured, up) in sorted(counts.items()):
            add(peers, list(key), configured)
            add(established, list(key), up)
        yield peers
        yield established
