"""Offline test support: a fake PyEZ device that answers RPCs from XML fixtures.

The fake mimics what PyEZ does on a real session. ``Device.rpc.<name>()``
returns the first child of the rpc-reply, namespaces are stripped from tags
and attributes, and an RPC without a fixture file raises ``RpcError`` just
like Junos rejecting an RPC for a protocol that is not configured.
"""

from __future__ import annotations

import pathlib

import pytest
from jnpr.junos.exception import RpcError
from jnpr.junos.jxml import remove_namespaces_and_spaces
from lxml import etree
from prometheus_client import Counter, generate_latest
from prometheus_client.parser import text_string_to_metric_families

from prometheus_network_exporter.collectors.junos.rpcs import fixture_name
from prometheus_network_exporter.collectors.junos.xmlutil import RPC_DECORATOR_ARGS, localname
from prometheus_network_exporter.devices.junosdevice import JuniperNetworkDevice

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "junos"
SYNTHETIC = FIXTURES / "synthetic"
ROUTING_TYPES = ("bgp", "bgp_details", "ospf", "ospf_details", "routes", "bfd")
# route_watch replaces the watch list of the routes type and has its own test.
CONTROL_PLANE_TYPES = (
    "probe",
    "routing_engine",
    "processes",
    "fpc",
    "alarms",
    "core_dumps",
    "system",
    "pfe",
    "pfe_exceptions",
    "pfe_hw_tables",
    "ddos",
    "krt",
    "rpd_memory",
    "fib",
    "ldp",
    "l2circuit",
    "pim",
    "neighbor_tables",
    "interface_errors",
    "logical_interfaces",
    "lacp",
    "lldp",
    "vxlan",
)
ALL_TYPES = ROUTING_TYPES + CONTROL_PLANE_TYPES
ROUTING_OPTIONS = {
    "tables": ["inet.0", "inet6.0"],
    "watch": ["0.0.0.0/0", "::/0", "203.0.113.0/25"],
    "young_route_seconds": 300,
}


def fixture_sets():
    return sorted(path for path in FIXTURES.iterdir() if path.is_dir())


def load_reply(path: pathlib.Path, strip: bool):
    root = etree.parse(str(path)).getroot()
    reply = root
    if localname(root) == "rpc-reply":
        children = [
            child
            for child in root
            if isinstance(child.tag, str) and localname(child) != "cli"
        ]
        reply = children[0]
    if strip:
        remove_namespaces_and_spaces(reply)
    return reply


class FakeRpc:
    def __init__(self, device, directory: pathlib.Path, strip: bool):
        self.device = device
        self.directory = directory
        self.strip = strip
        self.calls = []

    def __getattr__(self, name):
        rpc = name.replace("-", "_")

        def call(**kwargs):
            # fixture_name ignores interface filters, except for the logical
            # interface collector that queries one interface per call.
            args = {k: v for k, v in kwargs.items() if k not in RPC_DECORATOR_ARGS}
            fixture = fixture_name(rpc, args)
            self.calls.append(fixture)
            path = self.directory / f"{fixture}.xml"
            if not path.exists():
                raise RpcError()
            # A PyEZ table sets a transform that strips namespaces for the
            # rest of the session; honour that like the real device would.
            return load_reply(path, self.strip or self.device.transform is not None)

        return call


class FakeDevice:
    """Stands in for ``jnpr.junos.Device`` without any network access."""

    _use_filter = False

    def __init__(self, directory: pathlib.Path, strip: bool = True):
        self.hostname = "switch.example.com"
        self.timeout = 30
        self.transform = None
        self.rpc = FakeRpc(self, directory, strip)
        # Unit tests call the collectors without collect(); act connected.
        self.connected = True
        self.opened = 0
        self.closed = 0

    def open(self):
        self.opened += 1
        self.connected = True
        return self

    def close(self):
        self.closed += 1
        self.connected = False


def make_device(
    directory: pathlib.Path,
    types=ALL_TYPES,
    options=None,
    strip: bool = True,
) -> JuniperNetworkDevice:
    counter = Counter(
        "exporter_exceptions",
        "exceptions",
        ["exception", "collector", "hostname"],
        registry=None,
    )
    device = JuniperNetworkDevice(
        "switch.example.com",
        types=list(types),
        exception_counter=counter,
        options=dict(options or {}),
    )
    device.device = FakeDevice(directory, strip=strip)
    # No DNS in tests; a deterministic reverse lookup instead.
    device.lookup = lambda ip: f"name-of-{ip}" if ip else ""
    return device


def scrape(device: JuniperNetworkDevice) -> str:
    device.begin_scrape()
    return generate_latest(device.registry).decode("utf-8")


def samples(text: str) -> dict:
    """``{sample_name: [(labels, value), ...]}`` from exposition text."""
    result = {}
    for family in text_string_to_metric_families(text):
        for sample in family.samples:
            result.setdefault(sample.name, []).append((dict(sample.labels), sample.value))
    return result


def value(found: dict, name: str, **labels):
    matches = [
        v
        for sample_labels, v in found.get(name, [])
        if all(sample_labels.get(k) == v2 for k, v2 in labels.items())
    ]
    assert len(matches) == 1, f"{name}{labels}: {matches!r}"
    return matches[0]


def labels_of(found: dict, name: str, **labels) -> dict:
    matches = [
        sample_labels
        for sample_labels, _ in found.get(name, [])
        if all(sample_labels.get(k) == v2 for k, v2 in labels.items())
    ]
    assert len(matches) == 1, f"{name}{labels}: {matches!r}"
    return matches[0]


@pytest.fixture
def synthetic():
    device = make_device(SYNTHETIC, options=ROUTING_OPTIONS)
    return samples(scrape(device))
