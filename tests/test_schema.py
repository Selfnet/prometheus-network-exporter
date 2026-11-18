"""The example config and every metric type the device knows pass the schema."""

import pathlib

import pytest
import yaml

voluptuous = pytest.importorskip("voluptuous")

from prometheus_network_exporter.devices.junosdevice import SIMPLE_COLLECTORS  # noqa: E402
from prometheus_network_exporter.schema import Configuration  # noqa: E402

CONFIG = pathlib.Path(__file__).parent.parent / "prometheus_network_exporter" / "config" / "config.yml"


def test_example_config_is_valid():
    Configuration().validate(yaml.safe_load(CONFIG.read_text()))


def test_every_metric_type_is_allowed():
    types = sorted(set(SIMPLE_COLLECTORS) | {"processes", "interface_errors", "logical_interfaces", "route_watch", "bgp_details", "ospf_details"})
    module = {"device": "junos", "auth": {"method": "ssh_key"}, "metrics": types}
    Configuration().validate({"m": module})


def test_unknown_junos_option_is_rejected():
    module = {"device": "junos", "auth": {"method": "ssh_key"}, "metrics": ["probe"], "junos": {"rpc_timout": 5}}
    with pytest.raises(voluptuous.Invalid):
        Configuration().validate({"m": module})
