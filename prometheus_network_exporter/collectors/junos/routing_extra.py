"""Routing state beyond BGP and OSPF.

KRT and FIB show whether the kernel keeps up with routing changes, rpd task
memory shows memory pressure in the routing daemon, LDP and l2circuit cover
the MPLS underlay, PIM the multicast neighbours, and the ARP/ND counts the
neighbour tables that share hardware space with the routes.
"""

from __future__ import annotations

import collections
import re

from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, InfoMetricFamily

from ..base import Collector
from . import base
from .rpcs import RPCS
from .xmlutil import (
    Reader,
    add,
    all_text,
    iter_items,
    label,
    localname,
    numeric_leaves,
    slug,
    state_set,
    text,
)

KRT_QUEUE_TEXT = re.compile(r"^\s*(?P<queue>[A-Za-z][^:]*?queue)\s*:\s*(?P<count>\d+)\s+queued", re.I)
KEY_VALUE_TEXT = re.compile(r"^\s*(?P<key>[A-Za-z][^:]*?)\s*:\s*(?P<value>-?\d+)\s*$")
LDP_SESSION_STATES = ("Operational", "Nonexistent", "Initialized", "OpenRec", "OpenSent", "Closing")
ND_STATES = ("reachable", "stale", "delay", "probe", "incomplete", "unreachable", "permanent")


class KRTCollector(Collector):
    """``show krt queue`` and ``show krt state``: kernel route table sync backlog."""

    name = "krt"

    def __init__(self, device):
        super().__init__(f"{base}_krt", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        queue = GaugeMetricFamily(
            f"{self.base_name}_queue_entries",
            "Entries waiting in the KRT queues; a growing queue means rpd or "
            "the kernel does not keep up with route changes",
            labels=["queue"],
        )
        state = GaugeMetricFamily(
            f"{self.base_name}_state",
            "Numeric fields of show krt state, field name as label",
            labels=["field"],
        )
        command, args = RPCS["krt_queue"]
        reply = self.device.rpc_reply(command, **args)
        if reply is not None:
            self._queues(reply, queue)
        command, args = RPCS["krt_state"]
        reply = self.device.rpc_reply(command, **args)
        if reply is not None:
            self._state(reply, state)
        yield from self.reader.unique((queue, state))

    def _queues(self, reply, queue) -> None:
        found = 0
        for item in iter_items(reply, ("krt-queue",)):
            name = text(item, "krtq-type")
            length = text(item, "krtq-queue-length")
            if name is not None and length is not None:
                queue.add_metric([slug(name)], float(length))
                found += 1
        if not found:
            for line in all_text(reply).splitlines():
                match = KRT_QUEUE_TEXT.match(line)
                if match:
                    queue.add_metric([slug(match.group("queue"))], float(match.group("count")))
                    found += 1
        if not found:
            self.reader.record("krt-queue")

    def _state(self, reply, state) -> None:
        fields = {}
        # Junos 21.4 nests the queue counters in krt-queue-state below
        # krt-state-information; older layouts used a flat krt-state.
        for item in iter_items(reply, ("krt-state", "krt-state-information", "krt-queue-state")):
            fields.update(numeric_leaves(item))
        if not fields:
            for line in all_text(reply).splitlines():
                match = KEY_VALUE_TEXT.match(line)
                if match:
                    fields[slug(match.group("key"))] = float(match.group("value"))
        if not fields:
            self.reader.record("krt-state")
        for field, value in sorted(fields.items()):
            state.add_metric([slug(field)], value)


class TaskMemoryCollector(Collector):
    """``show task memory``: overall rpd memory use."""

    name = "task_memory"

    def __init__(self, device):
        super().__init__(f"{base}_rpd_task_memory", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        command, args = RPCS["task_memory"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        memory = GaugeMetricFamily(
            self.base_name,
            "Numeric fields of the overall report of show task memory, field name as label",
            labels=["field"],
        )
        fields = {}
        for element in reply.iter():
            if isinstance(element.tag, str) and localname(element).endswith("overall-report"):
                fields.update(numeric_leaves(element))
        if not fields:
            fields.update(numeric_leaves(reply))
        if not fields:
            self.reader.record("task-memory-overall-report")
        for field, value in sorted(fields.items()):
            memory.add_metric([slug(field)], value)
        yield from self.reader.unique((memory,))


class ForwardingTableCollector(Collector):
    """``show route forwarding-table summary``: what the kernel actually installed."""

    name = "fib_summary"

    def __init__(self, device):
        super().__init__(f"{base}_fib", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        command, args = RPCS["fib_summary"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        read = self.reader
        routes = GaugeMetricFamily(
            f"{self.base_name}_routes",
            "Routes in the forwarding table per table and route type",
            labels=["table", "bridge_domain", "family", "type"],
        )
        for table in iter_items(reply, ("route-table",)):
            summaries = list(iter_items(table, ("route-table-summary",)))
            if not summaries and text(table, "table-name") is None:
                # Junos emits empty route-table elements as separators.
                continue
            labels = [
                label(read.text(table, "table-name")),
                label(text(table, "bd-name")),
                label(read.text(table, "address-family", required=False)),
            ]
            for summary in summaries:
                add(
                    routes,
                    labels + [label(read.text(summary, "route-table-type"))],
                    read.number(summary, "route-count"),
                )
        yield from read.unique((routes,))


class LDPCollector(Collector):
    """LDP sessions and hello adjacencies."""

    name = "ldp"

    def __init__(self, device):
        super().__init__(f"{base}_ldp", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        read = self.reader
        session_state = GaugeMetricFamily(
            f"{self.base_name}_session_state",
            "LDP session state, 1 for the current one",
            labels=["neighbor", "neighbor_name", "state"],
        )
        session_up = GaugeMetricFamily(
            f"{self.base_name}_session_up_seconds",
            "Seconds since the LDP session came up",
            labels=["neighbor", "neighbor_name"],
        )
        sessions = GaugeMetricFamily(f"{self.base_name}_sessions", "LDP sessions")
        command, args = RPCS["ldp_session"]
        reply = self.device.rpc_reply(command, **args)
        if reply is not None:
            count = 0
            sessions_seen = list(iter_items(reply, ("ldp-session",)))
            self.device.prefetch(text(s, "ldp-neighbor-address") for s in sessions_seen)
            for session in sessions_seen:
                address = label(read.text(session, "ldp-neighbor-address"))
                labels = [address, label(self.device.lookup(address))]
                current = read.text(session, "ldp-session-state")
                if not state_set(session_state, labels, current, LDP_SESSION_STATES):
                    read.unexpected_state("ldp-session-state", current)
                add(session_up, labels, read.seconds(session, "ldp-session-up-time", required=False))
                count += 1
            sessions.add_metric([], float(count))

        neighbors = GaugeMetricFamily(
            f"{self.base_name}_neighbors", "LDP hello adjacencies per interface", labels=["interface"]
        )
        hold = GaugeMetricFamily(
            f"{self.base_name}_neighbor_hold_remaining_seconds",
            "Seconds until the hello adjacency expires",
            labels=["interface", "neighbor"],
        )
        command, args = RPCS["ldp_neighbor"]
        reply = self.device.rpc_reply(command, **args)
        if reply is not None:
            per_interface = collections.Counter()
            for neighbor in iter_items(reply, ("ldp-neighbor",)):
                interface = label(
                    read.first_text(neighbor, ("ldp-neighbor-interface", "interface-name"))
                )
                per_interface[interface] += 1
                add(
                    hold,
                    [interface, label(read.text(neighbor, "ldp-neighbor-address"))],
                    read.number(neighbor, "ldp-remaining-time", required=False),
                )
            for interface, count in sorted(per_interface.items()):
                neighbors.add_metric([interface], float(count))
        yield from read.unique((session_state, session_up, sessions, neighbors, hold))


class L2CircuitCollector(Collector):
    """``show l2circuit connections``: pseudowires over LDP."""

    name = "l2circuit"

    def __init__(self, device):
        super().__init__(f"{base}_l2circuit", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        command, args = RPCS["l2circuit"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        read = self.reader
        labels = ["neighbor", "connection"]
        up = GaugeMetricFamily(f"{self.base_name}_up", "1 when the pseudowire is Up", labels=labels)
        transitions = CounterMetricFamily(
            f"{self.base_name}_up_transitions", "Times the pseudowire went Up", labels=labels
        )
        info = InfoMetricFamily(self.base_name, "Pseudowire status code", labels=labels)
        for neighbor in iter_items(reply, ("l2circuit-neighbor",)):
            address = label(read.text(neighbor, "neighbor-address"))
            for connection in iter_items(neighbor, ("connection",)):
                labels_ = [address, label(read.text(connection, "connection-id"))]
                status = read.text(connection, "connection-status")
                up.add_metric(labels_, 1.0 if (status or "").lower() == "up" else 0.0)
                add(transitions, labels_, read.number(connection, "up-transitions", required=False))
                info.add_metric(
                    labels_,
                    {
                        "status": label(status),
                        "type": label(read.text(connection, "connection-type", required=False)),
                        "remote_pe": label(read.text(connection, "remote-pe", required=False)),
                    },
                )
        yield from read.unique((up, transitions, info))


class PIMCollector(Collector):
    """``show pim neighbors``."""

    name = "pim"

    def __init__(self, device):
        super().__init__(f"{base}_pim", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        command, args = RPCS["pim_neighbors"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        read = self.reader
        neighbors = GaugeMetricFamily(
            f"{self.base_name}_neighbors", "PIM neighbours per interface", labels=["interface"]
        )
        up = GaugeMetricFamily(
            f"{self.base_name}_neighbor_up_seconds",
            "Seconds since the PIM neighbour came up",
            labels=["interface", "neighbor"],
        )
        # Junos 21.4 names the interface inside each pim-neighbor; an
        # interface without neighbours may carry the name itself.
        counts = collections.Counter()
        for interface in iter_items(reply, ("pim-interface",)):
            found = list(iter_items(interface, ("pim-neighbor",)))
            if not found:
                name = text(interface, "pim-interface-name")
                if name is not None:
                    counts[name] += 0
                continue
            for neighbor in found:
                name = label(
                    read.text(neighbor, "pim-interface-name", required=False)
                    or text(interface, "pim-interface-name")
                )
                counts[name] += 1
                add(
                    up,
                    [name, label(read.text(neighbor, "pim-neighbor-address"))],
                    read.first_seconds(neighbor, ("pim-neighbor-uptime", "neighbor-uptime")),
                )
        for name, count in sorted(counts.items()):
            neighbors.add_metric([name], float(count))
        yield from read.unique((neighbors, up))


class NeighborTableCollector(Collector):
    """ARP and IPv6 neighbour table sizes."""

    name = "neighbor_tables"

    def __init__(self, device):
        super().__init__(f"{base}", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        read = self.reader
        arp = GaugeMetricFamily(f"{self.base_name}_arp_entries", "ARP table entries")
        command, args = RPCS["arp_table"]
        reply = self.device.rpc_reply(command, **args)
        if reply is not None:
            total = read.number(reply, ".//arp-entry-count", required=False)
            if total is None:
                total = float(sum(1 for _ in iter_items(reply, ("arp-table-entry",))))
            arp.add_metric([], total)

        nd = GaugeMetricFamily(
            f"{self.base_name}_nd_entries", "IPv6 neighbour entries per state", labels=["state"]
        )
        command, args = RPCS["nd_table"]
        reply = self.device.rpc_reply(command, **args)
        if reply is not None:
            counts = collections.Counter({state: 0 for state in ND_STATES + ("unknown",)})
            for entry in iter_items(reply, ("ipv6-nd-entry",)):
                state = (read.text(entry, "ipv6-nd-state") or "").lower()
                counts[state if state in ND_STATES else "unknown"] += 1
            for state, count in sorted(counts.items()):
                nd.add_metric([state], float(count))
        yield from read.unique((arp, nd))
