"""Forwarding plane metrics: PFE counters, hardware tables and DDoS protection.

The PFE replies differ between platforms and releases, and only part of them
could be checked without a device. The collectors therefore export the
numeric leaves of a section generically, with the Junos field name as a
label, instead of hard coding field names that may not exist.
"""

from __future__ import annotations

import re

from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from ..base import Collector
from . import base
from .rpcs import RPCS
from .xmlutil import Reader, add, all_text, iter_items, label, localname, number, numeric_leaves, slug, text

HW_TABLE_ROW = re.compile(
    r"^\s*(?P<table>[A-Za-z][\w ()<>/.-]*?)\s+(?P<max>\d+)\s+(?P<used>\d+)\s+(?P<free>\d+)(\s+[\d.]+)?\s*$"
)
# "sw error      5    1024": name, packets and optionally bytes; the name
# ends in a letter or bracket so that a number column is never part of it.
EXCEPTION_ROW = re.compile(
    r"^\s*(?P<name>[A-Za-z][\w ()/.,-]*?[A-Za-z)])\s{2,}(?P<count>\d+)(\s+\d+)*\s*$"
)


class PFEStatisticsCollector(Collector):
    """``show pfe statistics traffic``: host path and hardware discard counters."""

    name = "pfe_traffic"

    def __init__(self, device):
        super().__init__(f"{base}_pfe", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        command, args = RPCS["pfe_traffic"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        packets = CounterMetricFamily(
            f"{self.base_name}_statistics",
            "PFE counters per section, e.g. section pfe-traffic-statistics counter "
            "software-input-control-plane-drops",
            labels=["section", "counter"],
        )
        rates = GaugeMetricFamily(
            f"{self.base_name}_statistics_rate",
            "PFE rates in packets per second as reported by the device",
            labels=["section", "counter"],
        )
        sections = [
            element
            for element in reply.iter()
            if isinstance(element.tag, str) and localname(element).endswith("-statistics") and len(element)
        ]
        if not any(localname(section) == "pfe-traffic-statistics" for section in sections):
            self.reader.record("pfe-traffic-statistics")
        for section in sections:
            name = localname(section)
            for counter, value in numeric_leaves(section):
                if counter.endswith("-pps") or "-rate" in counter:
                    rates.add_metric([name, counter], value)
                else:
                    packets.add_metric([name, counter], value)
        yield from self.reader.unique((packets, rates))


class PFEExceptionCollector(Collector):
    """``show pfe statistics exceptions``; not every platform supports it."""

    name = "pfe_exceptions"

    def __init__(self, device):
        super().__init__(f"{base}_pfe_exceptions", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        command, args = RPCS["pfe_exceptions"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        exceptions = CounterMetricFamily(
            self.base_name, "PFE exception counters by type", labels=["type"]
        )
        found = {}
        structured = [
            element
            for element in reply.iter()
            if isinstance(element.tag, str) and len(element) and any(True for _ in numeric_leaves(element))
        ]
        for element in structured:
            for name, value in numeric_leaves(element):
                found[name] = found.get(name, 0.0) + value
        if not found:
            for line in all_text(reply).splitlines():
                match = EXCEPTION_ROW.match(line)
                if match:
                    name = slug(match.group("name"))
                    found[name] = found.get(name, 0.0) + float(match.group("count"))
        if not found:
            self.reader.record("output:exception-rows")
        for name, value in sorted(found.items()):
            exceptions.add_metric([name], value)
        yield from self.reader.unique((exceptions,))


class HardwareTableCollector(Collector):
    """``show pfe route summary hw``: LPM, host and multicast table usage.

    QFX5100/EX4600 print this only as a text table with the columns
    Type, Max, Used, Free and % free, one block per unit.
    """

    name = "pfe_hw_routes"

    def __init__(self, device):
        super().__init__(f"{base}_pfe_hw_table", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        command, args = RPCS["pfe_hw_routes"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        labels = ["unit", "table"]
        maximum = GaugeMetricFamily(
            f"{self.base_name}_max_entries", "Capacity of the hardware table", labels=labels
        )
        used = GaugeMetricFamily(
            f"{self.base_name}_used_entries", "Used entries of the hardware table", labels=labels
        )
        unit = "0"
        rows = 0
        for line in all_text(reply).splitlines():
            match = re.match(r"^\s*Unit:?\s*(\d+)", line)
            if match:
                unit = match.group(1)
                continue
            match = HW_TABLE_ROW.match(line)
            if not match or match.group("table").strip().lower() == "type":
                continue
            table = slug(match.group("table").replace("<", " lt ").replace(">", " gt "))
            maximum.add_metric([unit, table], float(match.group("max")))
            used.add_metric([unit, table], float(match.group("used")))
            rows += 1
        if not rows:
            self.reader.record("output:table-rows")
        yield from self.reader.unique((maximum, used))


class DDoSCollector(Collector):
    """DDoS protection: per protocol counters and active violations."""

    name = "ddos"

    def __init__(self, device):
        super().__init__(f"{base}_ddos", device, config={})
        self.reader = Reader(device.schema, self.name)

    def _protocol_labels(self, protocol):
        """Group name and packet type of a ddos-protocol entry.

        Junos 21.4 puts both into ddos-system-statistics; older layouts may
        carry the group name on the enclosing ddos-protocol-group.
        """
        group = text(protocol, ".//group-name")
        if group is None and protocol.getparent() is not None:
            group = text(protocol.getparent(), "group-name")
        packet_type = text(protocol, ".//packet-type")
        if group is None:
            self.reader.record("group-name")
        if packet_type is None:
            self.reader.record("packet-type")
        return [label(group), label(packet_type)]

    def _statistics(self, reply, packets, rates):
        for protocol in iter_items(reply, ("ddos-protocol",)):
            labels = self._protocol_labels(protocol)
            stats = next(iter_items(protocol, ("ddos-system-statistics",)), protocol)
            for counter, value in numeric_leaves(stats):
                if "rate" in counter:
                    rates.add_metric(labels + [counter], value)
                else:
                    packets.add_metric(labels + [counter], value)

    def collect(self):
        read = self.reader
        packets = CounterMetricFamily(
            f"{self.base_name}_packets",
            "DDoS protection counters across all locales, e.g. packet-received and packet-dropped",
            labels=["group", "packet_type", "counter"],
        )
        rates = GaugeMetricFamily(
            f"{self.base_name}_rate_pps",
            "DDoS protection arrival rates",
            labels=["group", "packet_type", "counter"],
        )
        command, args = RPCS["ddos_statistics"]
        reply = self.device.rpc_reply(command, **args)
        if reply is not None:
            self._statistics(reply, packets, rates)

        violations = GaugeMetricFamily(
            f"{self.base_name}_violations", "Protocols currently in violation"
        )
        violating = GaugeMetricFamily(
            f"{self.base_name}_violation_active",
            "1 for each protocol currently in violation",
            labels=["group", "packet_type"],
        )
        command, args = RPCS["ddos_violations"]
        reply = self.device.rpc_reply(command, **args)
        if reply is not None:
            entries = 0
            for protocol in iter_items(reply, ("ddos-protocol",)):
                violating.add_metric(self._protocol_labels(protocol), 1.0)
                entries += 1
            total = number(
                text(reply, ".//packet-types-in-violation") or text(reply, ".//total-violations")
            )
            add(violations, [], total if total is not None else float(entries))
        yield from read.unique((packets, rates, violations, violating))
