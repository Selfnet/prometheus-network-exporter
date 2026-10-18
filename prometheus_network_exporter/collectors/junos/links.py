"""Interface detail and layer 2 metrics.

``InterfaceErrorCollector`` reads ``show interfaces extensive`` once and
exports every error counter Junos lists plus the CoS queue counters, for the
ports whose description matches a pattern (core links and servers by
default). The other collectors cover logical units, LACP, LLDP and the
EVPN-VXLAN overlay.
"""

from __future__ import annotations

import collections
import re
from typing import Iterable, Optional

from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, InfoMetricFamily

from ..base import Collector
from . import base
from .rpcs import INTERFACE_RPC, RPCS, logical_interface_args
from .xmlutil import (
    Reader,
    add,
    all_text,
    find,
    iter_items,
    label,
    localname,
    numeric_leaves,
    slug,
    state_set,
    text,
)

DEFAULT_EXTENSIVE_INTERFACES = "[ex][et]-*"
DEFAULT_EXTENSIVE_DESCRIPTION = r"^(Core|Server|Uplink)"
DEFAULT_LOGICAL_INTERFACES = ("lo0", "irb")
# Ethernet MAC statistics also carry plain traffic counters; only keep the
# ones that describe a fault or flow control.
MAC_ERROR_FIELDS = re.compile(r"error|crc|fifo|pause|oversized|jabber|fragment|violation|runt|discard")
ERROR_SECTIONS = (
    ("input", "input-error-list"),
    ("output", "output-error-list"),
    ("mac", "ethernet-mac-statistics"),
)
LACP_MUX_STATES = (
    "Detached",
    "Waiting",
    "Attached",
    "Collecting",
    "Distributing",
    "Collecting distributing",
)
VTEP_ROW = re.compile(
    r"^\s*(?P<vtep>\d+\.\d+\.\d+\.\d+|[0-9a-fA-F]*:[0-9a-fA-F:]+)\s+\d+\s+vtep\.\d+"
)
VNI_ROW = re.compile(r"^\s+(?P<vni>\d+)\s+(\d+\.\d+\.\d+\.\d+|[0-9a-fA-F:]+)\s*$")
LACP_RECEIVE_STATES = ("Current", "Expired", "Defaulted", "Initialize", "LACP disabled", "Port disabled")


class InterfaceErrorCollector(Collector):
    """Error, carrier, MTU and queue counters from ``show interfaces extensive``."""

    name = "interface_extensive"

    def __init__(
        self,
        device,
        interfaces: str = DEFAULT_EXTENSIVE_INTERFACES,
        description: Optional[str] = DEFAULT_EXTENSIVE_DESCRIPTION,
    ):
        super().__init__(f"{base}_interface", device, config={})
        self.reader = Reader(device.schema, self.name)
        self.interfaces = interfaces
        self.description = re.compile(description) if description else None

    def collect(self):
        command, args = RPCS["interface_extensive"]
        reply = self.device.rpc_reply(command, **args, interface_name=self.interfaces)
        if reply is None:
            return
        read = self.reader
        errors = CounterMetricFamily(
            f"{self.base_name}_errors",
            "Error counters of show interfaces extensive; list is input, output "
            "or mac, counter the Junos field name with underscores",
            labels=["interface", "description", "list", "counter"],
        )
        queues = CounterMetricFamily(
            f"{self.base_name}_queue_packets",
            "CoS queue packet counters; kind is queued, trans, total_drop, "
            "tail_drop, red and so on, as Junos names them",
            labels=["interface", "description", "queue", "forwarding_class", "kind"],
        )
        for interface in iter_items(reply, ("physical-interface",)):
            name = read.text(interface, "name")
            description = text(interface, "description") or ""
            if name is None or (self.description and not self.description.search(description)):
                continue
            self._errors(errors, interface, [name, description])
            self._queues(queues, interface, [name, description])
        yield from read.unique((errors, queues))

    def _errors(self, errors, interface, labels):
        for list_name, section in ERROR_SECTIONS:
            element = find(interface, section)
            if element is None:
                if list_name != "mac":
                    self.reader.record(section)
                continue
            for counter, value in numeric_leaves(element):
                if list_name == "mac" and not MAC_ERROR_FIELDS.search(counter):
                    continue
                errors.add_metric(labels + [list_name, counter.replace("-", "_")], value)

    @staticmethod
    def _queues(queues, interface, labels):
        for queue in iter_items(interface, ("queue",)):
            number = text(queue, "queue-number")
            if number is None:
                continue
            queue_labels = labels + [number, label(text(queue, "forwarding-class-name"))]
            for field, value in numeric_leaves(queue):
                if not field.endswith("-packets"):
                    continue
                kind = field.replace("queue-counters-", "").replace("-packets", "").replace("-", "_")
                queues.add_metric(queue_labels + [kind], value)


class LogicalInterfaceCollector(Collector):
    """Traffic of logical units such as ``lo0.0`` and ``irb.<vlan>``."""

    name = "logical_interfaces"

    def __init__(self, device, interfaces: Iterable[str] = DEFAULT_LOGICAL_INTERFACES):
        super().__init__(f"{base}_logical_interface", device, config={})
        self.reader = Reader(device.schema, self.name)
        self.interfaces = list(interfaces)

    def collect(self):
        read = self.reader
        names = (
            ("received_bytes", "input-bytes", "Bytes received on the logical unit"),
            ("transmitted_bytes", "output-bytes", "Bytes sent on the logical unit"),
            ("received_packets", "input-packets", "Packets received on the logical unit"),
            ("transmitted_packets", "output-packets", "Packets sent on the logical unit"),
        )
        families = {
            suffix: CounterMetricFamily(f"{self.base_name}_{suffix}", doc, labels=["interface", "description"])
            for suffix, _, doc in names
        }
        for physical in self.interfaces:
            reply = self.device.rpc_reply(INTERFACE_RPC, **logical_interface_args(physical))
            if reply is None:
                continue
            for unit in iter_items(reply, ("logical-interface",)):
                name = read.text(unit, "name")
                if name is None:
                    continue
                labels = [name, label(text(unit, "description"))]
                statistics = find(unit, "traffic-statistics")
                if statistics is None:
                    read.record("logical-interface/traffic-statistics")
                    continue
                for suffix, field, _ in names:
                    add(families[suffix], labels, read.number(statistics, field))
        yield from read.unique(families.values())


class LACPCollector(Collector):
    """``show lacp interfaces``: member state of every LAG."""

    name = "lacp"

    def __init__(self, device):
        super().__init__(f"{base}_lacp", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        command, args = RPCS["lacp"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        read = self.reader
        labels = ["lag", "interface"]
        mux = GaugeMetricFamily(
            f"{self.base_name}_member_mux_state", "LACP mux state of the member link", labels=labels + ["state"]
        )
        receive = GaugeMetricFamily(
            f"{self.base_name}_member_receive_state",
            "LACP receive state of the member link",
            labels=labels + ["state"],
        )
        distributing = GaugeMetricFamily(
            f"{self.base_name}_member_distributing",
            "1 when the member link collects and distributes traffic",
            labels=labels,
        )
        for lag in iter_items(reply, ("lacp-interface-information",)):
            name = label(read.text(lag, "lag-lacp-header/aggregate-name"))
            for protocol in iter_items(lag, ("lag-lacp-protocol",)):
                member = [name, label(read.text(protocol, "name"))]
                current = read.text(protocol, "lacp-mux-state")
                if not state_set(mux, member, current, LACP_MUX_STATES):
                    read.unexpected_state("lacp-mux-state", current)
                current_receive = read.text(protocol, "lacp-receive-state")
                if not state_set(receive, member, current_receive, LACP_RECEIVE_STATES):
                    read.unexpected_state("lacp-receive-state", current_receive)
                distributing.add_metric(
                    member, 1.0 if (current or "").lower() == "collecting distributing" else 0.0
                )
        yield from read.unique((mux, receive, distributing))


class LLDPCollector(Collector):
    """``show lldp neighbors``: who is cabled to which port."""

    name = "lldp"

    def __init__(self, device):
        super().__init__(f"{base}_lldp", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        command, args = RPCS["lldp"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        read = self.reader
        neighbors = GaugeMetricFamily(f"{self.base_name}_neighbors", "LLDP neighbours")
        info = InfoMetricFamily(
            f"{self.base_name}_neighbor",
            "LLDP neighbour seen on a local port",
            labels=["interface", "remote_chassis_id"],
        )
        count = 0
        for neighbor in iter_items(reply, ("lldp-neighbor-information",)):
            interface = label(read.first_text(neighbor, ("lldp-local-port-id", "lldp-local-interface")))
            info.add_metric(
                [interface, label(read.text(neighbor, "lldp-remote-chassis-id", required=False))],
                {
                    "parent_interface": label(
                        text(neighbor, "lldp-local-parent-interface-name")
                    ),
                    "remote_system": label(read.text(neighbor, "lldp-remote-system-name", required=False)),
                    "remote_port": label(
                        read.first_text(
                            neighbor,
                            ("lldp-remote-port-description", "lldp-remote-port-id"),
                            required=False,
                        )
                    ),
                },
            )
            count += 1
        neighbors.add_metric([], float(count))
        yield from read.unique((neighbors, info))


class VxlanCollector(Collector):
    """EVPN-VXLAN: remote VTEPs and the MAC table summary.

    Both commands were not available as captures; the parsing is
    deliberately generic and every unparsed reply is reported in
    ``pyez_junos_xml_missing_fields``.
    """

    name = "vxlan"

    def __init__(self, device):
        super().__init__(f"{base}_vxlan", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        read = self.reader
        vteps = GaugeMetricFamily(f"{self.base_name}_remote_vteps", "Remote VTEPs known to this switch")
        vnis = GaugeMetricFamily(
            f"{self.base_name}_remote_vtep_vnis", "VNIs shared with the remote VTEP", labels=["vtep"]
        )
        command, args = RPCS["vxlan_remote_vteps"]
        reply = self.device.rpc_reply(command, **args)
        if reply is not None:
            per_vtep = self._remote_vteps(reply)
            if per_vtep is None:
                # Unknown, not zero.
                read.record("remote-vtep-address")
            else:
                vteps.add_metric([], float(len(per_vtep)))
                for vtep, count in sorted(per_vtep.items()):
                    vnis.add_metric([vtep], float(count))

        macs = GaugeMetricFamily(
            f"{base}_mac_table",
            "Numeric fields of show ethernet-switching table summary, per VLAN where reported",
            labels=["vlan", "field"],
        )
        command, args = RPCS["mac_table_summary"]
        reply = self.device.rpc_reply(command, **args)
        if reply is not None:
            self._mac_summary(reply, macs)
        yield from read.unique((vteps, vnis, macs))

    def _remote_vteps(self, reply) -> Optional[collections.Counter]:
        """VNIs per remote VTEP from XML elements or the text table, None if unparsable."""
        per_vtep = collections.Counter()
        addresses = [
            element
            for element in reply.iter()
            if isinstance(element.tag, str) and localname(element) == "remote-vtep-address"
        ]
        for address in addresses:
            vtep = (address.text or "").strip()
            if vtep:
                per_vtep[vtep] += sum(
                    1
                    for element in address.getparent().iter()
                    if isinstance(element.tag, str) and localname(element) in ("vn-id", "vni")
                )
        if addresses:
            return per_vtep
        if any(
            isinstance(element.tag, str) and localname(element) == "source-vtep-address"
            for element in reply.iter()
        ):
            # A switch with its own VTEP but no remote ones: zero, not unknown.
            return per_vtep
        # Text form: a row "<RVTEP-IP> <IFL-Idx> vtep.<n> <NH-Id> <mode>" starts
        # a remote VTEP, the indented "<VNID> <MC-Group-IP>" rows below it are its VNIs.
        parsed = False
        current = None
        for line in all_text(reply).splitlines():
            match = VTEP_ROW.match(line)
            if match:
                current = match.group("vtep")
                per_vtep[current] += 0
                parsed = True
                continue
            if "RVTEP-IP" in line or "Logical System" in line:
                parsed = True
                current = None
                continue
            if current is not None and VNI_ROW.match(line):
                per_vtep[current] += 1
        return per_vtep if parsed else None

    def _mac_summary(self, reply, macs) -> None:
        found = 0
        for element in reply.iter():
            if not isinstance(element.tag, str) or not len(element):
                continue
            vlan = text(element, "l2ng-l2-vlan-name") or text(element, "vlan-name") or ""
            for field, value in numeric_leaves(element):
                if re.search(r"count|entries|learned|mac", field):
                    macs.add_metric([vlan, slug(field)], value)
                    found += 1
        if not found:
            for match in re.finditer(r"(\d+)\s+entries,\s*(\d+)\s+learned", all_text(reply)):
                macs.add_metric(["", "entries"], float(match.group(1)))
                macs.add_metric(["", "learned"], float(match.group(2)))
                found += 1
        if not found:
            self.reader.record("output:mac-summary")
