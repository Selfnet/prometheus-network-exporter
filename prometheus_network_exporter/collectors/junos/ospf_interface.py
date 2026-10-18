"""OSPF and OSPFv3 interface metrics from ``show ospf interface detail``."""

from __future__ import annotations

from prometheus_client.core import GaugeMetricFamily, InfoMetricFamily

from ..base import Collector
from . import base
from .rpcs import OSPF_PROTOCOLS
from .xmlutil import Reader, add, find, iter_items, label, state_set

INTERFACE_STATES = ("Down", "Loop", "Waiting", "PtToPt", "DRother", "BDR", "DR")
LABELS = ["interface", "area"]
ITEMS = ("ospf-interface", "ospf3-interface")
GAUGES = (
    ("cost", "interface-cost", "OSPF metric of the interface"),
    ("neighbors", "neighbor-count", "Neighbours seen on the interface"),
    ("adjacencies", "adj-count", "Full adjacencies on the interface"),
    ("hello_interval_seconds", "hello-interval", "Configured hello interval"),
    ("dead_interval_seconds", "dead-interval", "Configured dead interval"),
    ("retransmit_interval_seconds", "retransmit-interval", "LSA retransmit interval"),
    ("mtu_bytes", "mtu", "MTU the interface announces in database description packets"),
)


class OSPFInterfaceCollector(Collector):
    def __init__(self, device, protocol: str = "ospf"):
        if protocol not in OSPF_PROTOCOLS:
            raise ValueError(f"Unsupported OSPF protocol: {protocol}")
        self.protocol = protocol
        super().__init__(f"{base}_{protocol}_interface", device, config={})
        self.reader = Reader(device.schema, f"{protocol}_interface")

    def collect(self):
        reply = self.device.rpc_reply(
            f"get_{self.protocol}_interface_information", detail=True
        )
        if reply is None:
            return
        read = self.reader
        state = GaugeMetricFamily(
            f"{self.base_name}_state",
            "OSPF interface state, 1 for the current state",
            labels=LABELS + ["state"],
        )
        gauges = {
            suffix: GaugeMetricFamily(f"{self.base_name}_{suffix}", doc, labels=LABELS)
            for suffix, _, doc in GAUGES
        }
        info = InfoMetricFamily(
            self.base_name, "OSPF interface configuration", labels=LABELS
        )
        for interface in iter_items(reply, ITEMS):
            labels = [
                label(read.text(interface, "interface-name")),
                label(read.text(interface, "ospf-area")),
            ]
            state_set(
                state, labels, read.text(interface, "ospf-interface-state"), INTERFACE_STATES
            )
            for suffix, field, _ in GAUGES:
                add(gauges[suffix], labels, read.number(interface, field))
            info.add_metric(
                labels,
                {
                    "type": label(read.text(interface, "interface-type")),
                    "dr_id": label(read.first_text(interface, ("dr-id", "dr-address"))),
                    "bdr_id": label(
                        read.first_text(interface, ("bdr-id", "bdr-address"))
                    ),
                    "passive": "yes" if find(interface, "passive") is not None else "no",
                    "authentication": label(
                        read.text(interface, "authentication-type", required=False)
                    ),
                    "stub_type": label(
                        read.text(interface, "ospf-stub-type", required=False)
                    ),
                },
            )
        yield state
        yield from gauges.values()
        yield info
