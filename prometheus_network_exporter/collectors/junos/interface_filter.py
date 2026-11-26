"""Keep only the interfaces whose description matches the option interface_description.

Access switches carry the members' ports next to the uplinks; their
descriptions name rooms and people. With the option set (e.g.
``^(Core|WIFI-AP): ``) the interface collector with its OSPF and optics
parts, the standalone optics, the transceiver inventory and the interface
addresses only export interfaces whose description matches. Without it
every interface is exported as before.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

from .rpcs import RPCS
from .xmlutil import iter_items, text

# Addresses on these parents belong to the switch itself, not to a port:
# loopback and management interfaces stay whatever their description says.
OWN_PARENTS = ("lo0", "em", "me", "fxp", "vme")


class DescriptionFilter:
    def __init__(self, pattern: Optional[str] = None) -> None:
        self.pattern = re.compile(pattern) if pattern else None

    def __bool__(self) -> bool:
        return self.pattern is not None

    def allows(self, description: Optional[str]) -> bool:
        if self.pattern is None:
            return True
        return bool(self.pattern.search(description or ""))

    def interfaces(self, interfaces: Optional[dict]) -> dict:
        """The entries of ``{name: values}`` whose values carry a matching description."""
        if interfaces is None or self.pattern is None:
            return interfaces or {}
        return {name: values for name, values in interfaces.items() if self.allows(dict(values).get("description"))}

    def parent_allowed(self, parent: str, descriptions: Dict[str, str]) -> bool:
        if self.pattern is None or parent.startswith(OWN_PARENTS):
            return True
        return self.allows(descriptions.get(parent))


def interface_descriptions(device) -> Dict[str, str]:
    """``{physical interface: description}`` from ``show interfaces descriptions``.

    Junos lists only interfaces that have a description; the reply is cached
    for the scrape, so several collectors share one round trip.
    """
    command, args = RPCS["interface_descriptions"]
    reply = device.rpc_reply(command, **args)
    if reply is None:
        return {}
    result = {}
    for interface in iter_items(reply, ("physical-interface",)):
        name = text(interface, "name")
        if name:
            result[name] = text(interface, "description") or ""
    return result
