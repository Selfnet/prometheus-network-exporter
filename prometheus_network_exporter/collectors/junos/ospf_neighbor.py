"""OSPF and OSPFv3 neighbour metrics from ``show ospf neighbor extensive``."""

from __future__ import annotations

from prometheus_client.core import GaugeMetricFamily, InfoMetricFamily

from ..base import Collector
from . import base
from .rpcs import OSPF_PROTOCOLS
from .xmlutil import Reader, add, iter_items, label, state_set, text

NEIGHBOR_STATES = (
    "Down",
    "Attempt",
    "Init",
    "2Way",
    "ExStart",
    "Exchange",
    "Loading",
    "Full",
)
LABELS = ["interface", "neighbor_id", "neighbor_name", "neighbor_address", "area"]
ITEMS = ("ospf-neighbor", "ospf3-neighbor")


class OSPFNeighborCollector(Collector):
    def __init__(self, device, protocol: str = "ospf"):
        if protocol not in OSPF_PROTOCOLS:
            raise ValueError(f"Unsupported OSPF protocol: {protocol}")
        self.protocol = protocol
        super().__init__(f"{base}_{protocol}_neighbor", device, config={})
        self.reader = Reader(device.schema, f"{protocol}_neighbor")

    def _gauge(self, suffix, doc, extra=()):
        return GaugeMetricFamily(
            f"{self.base_name}_{suffix}", doc, labels=LABELS + list(extra)
        )

    def collect(self):
        reply = self.device.rpc_reply(
            f"get_{self.protocol}_neighbor_information", extensive=True
        )
        if reply is None:
            return
        read = self.reader
        state = self._gauge(
            "state",
            "OSPF neighbour state machine state, 1 for the current state. "
            "2Way is normal between two DROther routers",
            ["state"],
        )
        up = self._gauge("up_seconds", "Seconds since the neighbour came up")
        adjacency = self._gauge(
            "adjacency_seconds", "Seconds since the adjacency reached Full"
        )
        dead = self._gauge(
            "dead_timer_seconds", "Seconds left on the neighbour dead timer"
        )
        priority = self._gauge("priority", "Router priority announced by the neighbour")
        info = InfoMetricFamily(
            self.base_name,
            "Designated and backup designated router seen with this neighbour",
            labels=LABELS,
        )

        neighbors = list(iter_items(reply, ITEMS))
        self.device.prefetch(text(neighbor, "neighbor-id") for neighbor in neighbors)
        for neighbor in neighbors:
            neighbor_id = read.text(neighbor, "neighbor-id")
            labels = [
                label(read.text(neighbor, "interface-name")),
                label(neighbor_id),
                self.device.lookup(neighbor_id) if neighbor_id else "",
                label(read.text(neighbor, "neighbor-address")),
                label(read.text(neighbor, "ospf-area")),
            ]
            current = read.text(neighbor, "ospf-neighbor-state")
            full = (current or "").lower() == "full"
            if not state_set(state, labels, current, NEIGHBOR_STATES):
                read.unexpected_state("ospf-neighbor-state", current)
            add(up, labels, read.seconds(neighbor, "neighbor-up-time", required=full))
            add(
                adjacency,
                labels,
                read.seconds(neighbor, "neighbor-adjacency-time", required=False),
            )
            add(dead, labels, read.number(neighbor, "activity-timer"))
            add(priority, labels, read.number(neighbor, "neighbor-priority"))
            info.add_metric(
                labels,
                {
                    "dr": label(read.first_text(neighbor, ("dr-address", "dr-id"))),
                    "bdr": label(read.first_text(neighbor, ("bdr-address", "bdr-id"))),
                    "options": label(read.text(neighbor, "options", required=False)),
                },
            )
        yield from read.unique((state, up, adjacency, dead, priority, info))
