"""Per peer BGP metrics from ``show bgp neighbor`` and ``show bgp summary``."""

from __future__ import annotations

from prometheus_client.core import (
    CounterMetricFamily,
    GaugeMetricFamily,
    InfoMetricFamily,
)

from ..base import Collector
from . import base
from .xmlutil import (
    Reader,
    add,
    findall,
    iter_items,
    label,
    seconds,
    state_set,
    strip_port,
    text,
)

BGP_STATES = ("Idle", "Connect", "Active", "OpenSent", "OpenConfirm", "Established")
# routing_instance keeps peers apart that share an address across VRFs.
PEER_LABELS = ["peer", "peername", "group", "routing_instance"]
RIB_COUNTERS = ("active", "received", "accepted", "suppressed", "advertised")
DIRECTIONS = (("in", "input"), ("out", "output"))


class BGPNeighborCollector(Collector):
    name = "bgp_neighbor"

    def __init__(self, device):
        super().__init__(f"{base}_bgp_peer", device, config={})
        self.reader = Reader(device.schema, self.name)

    def _gauge(self, suffix, doc, extra=()):
        return GaugeMetricFamily(
            f"{self.base_name}_{suffix}", doc, labels=PEER_LABELS + list(extra)
        )

    def _counter(self, suffix, doc, extra=()):
        return CounterMetricFamily(
            f"{self.base_name}_{suffix}", doc, labels=PEER_LABELS + list(extra)
        )

    def _uptimes(self) -> dict:
        """Seconds in the current state per peer, only ``show bgp summary`` has it."""
        summary = self.device.rpc_reply("get_bgp_summary_information")
        if summary is None:
            return {}
        result = {}
        for peer in iter_items(summary, ("bgp-peer",)):
            address = strip_port(text(peer, "peer-address"))
            value = seconds(peer, "elapsed-time")
            if address and value is not None:
                result[address] = value
        return result

    def collect(self):
        reply = self.device.rpc_reply("get_bgp_neighbor_information")
        if reply is None:
            return
        read = self.reader
        uptimes = self._uptimes()

        state = self._gauge(
            "state",
            "BGP finite state machine state of the peer, 1 for the current state",
            ["state"],
        )
        state_seconds = self._gauge(
            "state_seconds", "Seconds the peer has been in its current state"
        )
        flaps = self._counter("flaps", "Times the session went down")
        messages = self._counter("messages", "BGP messages", ["direction"])
        updates = self._counter("updates", "BGP UPDATE messages", ["direction"])
        refreshes = self._counter(
            "refreshes", "BGP ROUTE-REFRESH messages", ["direction"]
        )
        octets = self._counter("octets", "BGP protocol bytes", ["direction"])
        errors = self._counter(
            "errors",
            "BGP NOTIFICATION messages by error name",
            ["error", "direction"],
        )
        hold_time = self._gauge("hold_time_seconds", "Negotiated hold time")
        keepalive = self._gauge(
            "keepalive_interval_seconds", "Negotiated keepalive interval"
        )
        queue = self._gauge(
            "output_queue_routes", "Routes waiting in the output queue", ["rib"]
        )
        ribs = {
            kind: self._gauge(
                f"rib_{kind}_prefixes",
                f"Prefixes {kind} in this RIB for the peer",
                ["rib"],
            )
            for kind in RIB_COUNTERS
        }
        info = InfoMetricFamily(
            self.base_name, "Static information about the BGP peer", labels=PEER_LABELS
        )
        last_event = InfoMetricFamily(
            f"{self.base_name}_last_event",
            "Last state, event and error seen on the session",
            labels=PEER_LABELS,
        )

        for peer in iter_items(reply, ("bgp-peer",)):
            address = strip_port(read.text(peer, "peer-address"))
            if not address:
                continue
            labels = [
                address,
                self.device.lookup(address),
                label(read.text(peer, "peer-group")),
                read.text(peer, "peer-cfg-rti", required=False) or "master",
            ]
            current = read.text(peer, "peer-state")
            established = (current or "").lower() == "established"
            if not state_set(state, labels, current, BGP_STATES):
                read.unexpected_state("peer-state", current)
            add(state_seconds, labels, uptimes.get(address))
            add(flaps, labels, read.number(peer, "flap-count"))
            # Junos reports the message counters only while a session exists;
            # a peer that never came up has none, which is not a schema gap.
            for direction, prefix in DIRECTIONS:
                for family, field in (
                    (messages, "messages"),
                    (updates, "updates"),
                    (refreshes, "refreshes"),
                    (octets, "octets"),
                ):
                    add(
                        family,
                        labels + [direction],
                        read.number(peer, f"{prefix}-{field}", required=established),
                    )
            for error in findall(peer, "bgp-error"):
                name = label(read.text(error, "name")) or "unknown"
                add(errors, labels + [name, "in"], read.number(error, "receive-count"))
                add(errors, labels + [name, "out"], read.number(error, "send-count"))
            add(
                hold_time,
                labels,
                read.number(peer, "active-holdtime", required=established),
            )
            add(
                keepalive,
                labels,
                read.number(peer, "keepalive-interval", required=established),
            )
            for entry in findall(peer, "bgp-output-queue"):
                add(
                    queue,
                    labels + [label(read.text(entry, "table-name"))],
                    read.number(entry, "count"),
                )
            for table in findall(peer, "bgp-rib"):
                rib = label(read.text(table, "name"))
                for kind, metric in ribs.items():
                    add(
                        metric,
                        labels + [rib],
                        read.number(
                            table,
                            f"{kind}-prefix-count",
                            required=kind != "advertised",
                        ),
                    )
            info.add_metric(
                labels,
                {
                    "peer_as": label(read.text(peer, "peer-as")),
                    "local_as": label(read.text(peer, "local-as")),
                    "peer_type": label(read.text(peer, "peer-type")),
                    "local_address": strip_port(read.text(peer, "local-address")),
                    "peer_id": label(read.text(peer, "peer-id", required=False)),
                    "local_id": label(read.text(peer, "local-id", required=False)),
                    "description": label(read.text(peer, "description", required=False)),
                    "address_families": label(
                        read.text(
                            peer,
                            "bgp-option-information/address-families",
                            required=False,
                        )
                    ),
                },
            )
            last_event.add_metric(
                labels,
                {
                    "last_state": label(read.text(peer, "last-state")),
                    "last_event": label(read.text(peer, "last-event")),
                    "last_error": label(read.text(peer, "last-error")),
                    "last_flap_event": label(
                        read.text(peer, "last-flap-event", required=False)
                    ),
                },
            )

        yield from read.unique(
            (
                state,
                state_seconds,
                flaps,
                messages,
                updates,
                refreshes,
                octets,
                errors,
                hold_time,
                keepalive,
                queue,
                *ribs.values(),
                info,
                last_event,
            )
        )
