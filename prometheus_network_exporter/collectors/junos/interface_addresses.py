"""Interface addresses for checking the subnets of LLDP link endpoints."""

import ipaddress

from prometheus_client.core import InfoMetricFamily

from ..base import Collector
from . import base
from .interface_filter import DescriptionFilter, interface_descriptions
from .rpcs import RPCS
from .xmlutil import findall, iter_items, text


def reported_network(local, destination, address):
    try:
        if "/" in local:
            return ipaddress.ip_interface(local).network
        if destination and "/" in destination:
            host, prefix = destination.split("/", 1)
            # Junos can abbreviate IPv4 networks, e.g. 192.0.2/24.
            if ":" not in host and 1 <= len(host.split(".")) < 4:
                host += ".0" * (4 - len(host.split(".")))
            network = ipaddress.ip_network(host + "/" + prefix, strict=False)
            if address.version == network.version and address in network:
                return network
    except ValueError:
        pass
    return None


def address_info(local, destination):
    if not local:
        return None
    try:
        address = ipaddress.ip_address(local.split("/", 1)[0])
    except ValueError:
        return None
    network = reported_network(local, destination, address)
    return {
        "address": str(address),
        "family": "inet" if address.version == 4 else "inet6",
        "prefix_length": str(network.prefixlen) if network is not None else "",
        "network": str(network) if network is not None else "",
    }


# Junos internal interfaces between routing engine and PFE, and the internal
# loopback units lo0.16384 and up.
INTERNAL_PARENTS = ("bme", "jsrv")
INTERNAL_LOOPBACK_UNIT = 16384


def internal_unit(parent, name):
    if parent.startswith(INTERNAL_PARENTS):
        return True
    unit = name.rpartition(".")[2]
    return parent == "lo0" and unit.isdigit() and int(unit) >= INTERNAL_LOOPBACK_UNIT


def unit_addresses(unit):
    for family in findall(unit, "address-family"):
        if text(family, "address-family-name") not in ("inet", "inet6"):
            continue
        for entry in findall(family, "interface-address"):
            values = address_info(text(entry, "ifa-local"), text(entry, "ifa-destination"))
            if values is None:
                continue
            address = ipaddress.ip_address(values["address"])
            # Link-local and loopback addresses say nothing about a link subnet.
            if address.is_link_local or address.is_loopback:
                continue
            yield values


class InterfaceAddressCollector(Collector):
    name = "interface_addresses"

    def __init__(self, device, description_filter=None):
        super().__init__(f"{base}_interface_address", device, config={})
        self.description_filter = description_filter or DescriptionFilter()

    def collect(self):
        command, args = RPCS["interface_addresses"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        info = InfoMetricFamily(
            self.base_name,
            "Interface address; blank prefix or routing instance means unknown",
            labels=["interface", "parent_interface", "routing_instance"],
        )
        # Only with the filter: the terse reply carries no descriptions.
        descriptions = interface_descriptions(self.device) if self.description_filter else {}
        seen = set()
        for physical in iter_items(reply, ("physical-interface",)):
            parent = text(physical, "name")
            if not parent or not self.description_filter.parent_allowed(parent, descriptions):
                continue
            for unit in findall(physical, "logical-interface"):
                name = text(unit, "name")
                if not name or internal_unit(parent, name):
                    continue
                routing_instance = text(unit, "routing-instance") or text(physical, "routing-instance") or ""
                for values in unit_addresses(unit):
                    key = (name, parent, routing_instance, tuple(sorted(values.items())))
                    if key not in seen:
                        info.add_metric([name, parent, routing_instance], values)
                        seen.add(key)
        yield info
