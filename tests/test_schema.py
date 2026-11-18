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
    types = sorted(
        set(SIMPLE_COLLECTORS)
        | {"processes", "interface_errors", "logical_interfaces", "route_watch", "bgp_details", "ospf_details"}
    )
    module = {"device": "junos", "auth": {"method": "ssh_key"}, "metrics": types}
    Configuration().validate({"m": module})


def test_unknown_junos_option_is_rejected():
    module = {"device": "junos", "auth": {"method": "ssh_key"}, "metrics": ["probe"], "junos": {"rpc_timout": 5}}
    with pytest.raises(voluptuous.Invalid):
        Configuration().validate({"m": module})


def test_schema_runs_as_script(monkeypatch):
    import runpy
    import sys

    monkeypatch.setattr(sys, "argv", ["schema.py", "prometheus_network_exporter/config/config.yml"])
    runpy.run_module("prometheus_network_exporter.schema", run_name="__main__")


def module(**overrides):
    return {"device": "junos", "auth": {"method": "ssh_key"}, "metrics": ["probe"], **overrides}


def test_only_junos_devices():
    for device in ("arubaos", "ios", "airmax"):
        with pytest.raises(voluptuous.Invalid):
            Configuration().validate({"m": module(device=device)})


def test_auth_options():
    auth = {"method": "ssh_key", "username": "pyez", "ssh_key": "~/.ssh/id", "ssh_config": "~/.ssh/config", "port": 22}
    Configuration().validate({"m": module(auth=auth)})
    Configuration().validate({"m": module(auth={"method": "password", "username": "u", "password": "p"})})
    for auth in ({"method": "token"}, {"method": "ssh_key", "verify": True}, {"method": "ssh_key", "port": "22"}):
        with pytest.raises(voluptuous.Invalid):
            Configuration().validate({"m": module(auth=auth)})


def test_every_allowed_metric_type_registers_a_collector():
    from unittest import mock

    from prometheus_network_exporter.devices.junosdevice import JuniperNetworkDevice

    allowed = Configuration().schema.schema[voluptuous.Required(str)][voluptuous.Required("metrics")]
    for name in allowed:
        # ospf only adds the OSPF neighbours to the interface collectors.
        types = [name, "interface"] if name == "ospf" else [name]
        with mock.patch.object(JuniperNetworkDevice, "_register") as register:
            JuniperNetworkDevice("switch.example.net", types=types, exception_counter=mock.Mock())
        assert register.called, f"metric type {name} registers no collector"
        if name == "ospf":
            nested = [type(c).__name__ for c in register.call_args_list[0].args[0].collectors]
            assert nested == ["OSPFCollector", "OSPF3Collector"]
