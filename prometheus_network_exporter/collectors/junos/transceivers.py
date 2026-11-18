"""Transceiver inventory, keyed by the physical FPC/PIC/port location."""

import re

from prometheus_client.core import InfoMetricFamily

from ..base import Collector
from . import base
from .rpcs import RPCS
from .xmlutil import LOGGER, iter_items, text

LOCATION = re.compile(r"^(FPC|PIC|Xcvr|Transceiver)\s+(\d+)$", re.IGNORECASE)
INTERFACE = re.compile(r"^[a-z]+-(\d+/\d+/\d+)(?::\d+)?$")


def inventory(reply):
    for node in reply.iter():
        if not isinstance(node.tag, str):
            continue
        match = LOCATION.fullmatch(text(node, "name") or "")
        if not match or match[1].lower() not in ("xcvr", "transceiver"):
            continue
        location = {"port": match[2]}
        for parent in node.iterancestors():
            match = LOCATION.fullmatch(text(parent, "name") or "")
            if match and match[1].lower() in ("fpc", "pic"):
                location.setdefault(match[1].lower(), match[2])
        if not all(key in location for key in ("fpc", "pic", "port")):
            continue
        yield "/".join(location[key] for key in ("fpc", "pic", "port")), {
            "manufacturer": text(node, "vendor-name") or text(node, "manufacturer") or "",
            "part_number": text(node, "vendor-part-number") or text(node, "part-number") or "",
            "serial_number": text(node, "serial-number") or "",
            "transceiver_type": text(node, "description") or "",
        }


class TransceiverCollector(Collector):
    name = "transceivers"

    def __init__(self, device):
        super().__init__(f"{base}_transceiver", device, config={})

    def collect(self):
        command, args = RPCS["transceivers"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        modules = {}
        conflicts = set()
        for module, values in inventory(reply):
            if module in modules and modules[module] != values:
                conflicts.add(module)
            modules.setdefault(module, values)
        for module in sorted(conflicts):
            # Two different modules at one location: report neither.
            LOGGER.warning(
                "transceivers: %s :: conflicting inventory for module %s, skipped", self.device.hostname, module
            )
            del modules[module]
        self.enrich_pic_inventory(modules)
        info = InfoMetricFamily(
            self.base_name, "Reported transceiver inventory; blank fields are unknown", labels=["module"]
        )
        for module, values in modules.items():
            info.add_metric([module], values)
        yield info
        # Link each logical breakout port to its one shared physical module.
        command, args = RPCS["interfaces_brief"]
        reply = self.device.rpc_reply(command, **args, interface_name="[efgx][et]-*")
        if reply is None:
            return
        ports = InfoMetricFamily(
            f"{base}_interface_transceiver", "Interface to physical module mapping", labels=["interface", "module"]
        )
        seen = set()
        for interface in iter_items(reply, ("physical-interface",)):
            name = text(interface, "name") or ""
            match = INTERFACE.fullmatch(name)
            if match and match[1] in modules and name not in seen:
                ports.add_metric([name, match[1]], {})
                seen.add(name)
        yield ports

    def enrich_pic_inventory(self, modules):
        for location in sorted({module.rsplit("/", 1)[0] for module in modules}):
            fpc, pic = location.split("/")
            command, args = RPCS["transceiver_pic"]
            details = self.device.rpc_reply(command, **args, fpc_slot=fpc, pic_slot=pic)
            if details is None:
                continue
            for port in iter_items(details, ("port",)):
                module = location + "/" + (text(port, "port-number") or "")
                if module not in modules:
                    continue
                # Junos documents sfp-vendor-pno; sfp-vendor-part-number is
                # accepted as well.
                for field, tags in (
                    ("manufacturer", ("sfp-vendor-name",)),
                    ("part_number", ("sfp-vendor-pno", "sfp-vendor-part-number")),
                ):
                    value = next(filter(None, (text(port, tag) for tag in tags)), None)
                    if value:
                        modules[module][field] = value
