"""The PyEZ table based IGMP and environment collectors."""

from unittest.mock import Mock

import yaml

from prometheus_network_exporter.devices.junosdevice import JuniperNetworkDevice
from prometheus_network_exporter.collectors.junos.environment import EnvironmentCollector
from prometheus_network_exporter.collectors.junos.igmp import IGMPCollector

IGMP_CONFIG = """
IGMP_NETWORKS:
  ignore:
    "239.195.255.255/32": list
    "239.192.255.0/24": test
  allow:
    "239.192.0.0/16": first
    "239.195.0.0/16": second
METRICS:
  Gauge:
    - metric: broadcasts
      key: broadcasts
      description: subscribers
LABELS:
  - label: broadcaster
    key: broadcaster
"""


def collect(collector):
    return {
        (s.name, tuple(sorted(s.labels.items()))): s.value for family in collector.collect() for s in family.samples
    }


def device(**values):
    device = Mock(spec=JuniperNetworkDevice)
    for name, value in values.items():
        getattr(device, name).return_value = value
    return device


def test_igmp_counts_each_group_once_outside_ignored_networks(tmp_path):
    config = tmp_path / "igmp.yaml"
    config.write_text(IGMP_CONFIG)
    igmp = {
        "irb.100": {"mgm_addresses": ["239.192.0.1", "239.192.0.2", "239.192.255.1", "239.195.255.255"]},
        "irb.200": {"mgm_addresses": ["239.195.0.7", "224.0.0.251"]},
    }
    collector = IGMPCollector(device(get_igmp=igmp), config_path=str(config))
    data = collect(collector)
    assert data[("pyez_junos_igmp_broadcasts", (("broadcaster", "first"),))] == 2
    assert data[("pyez_junos_igmp_broadcasts", (("broadcaster", "second"),))] == 1
    # The families are flushed after each scrape: a second scrape does not add up.
    assert collect(collector) == data


def test_igmp_without_ignore_list_still_counts(tmp_path):
    config = yaml.safe_load(IGMP_CONFIG)
    del config["IGMP_NETWORKS"]["ignore"]
    path = tmp_path / "igmp.yaml"
    path.write_text(yaml.safe_dump(config))
    collector = IGMPCollector(device(get_igmp={"irb.1": {"mgm_addresses": ["239.192.0.1"]}}), config_path=str(path))
    assert collect(collector)[("pyez_junos_igmp_broadcasts", (("broadcaster", "first"),))] == 1


def test_default_igmp_config_loads():
    collector = IGMPCollector(device(get_igmp={}))
    assert all(value == 0 for value in collect(collector).values())
    assert len(collector.allowed_networks) == 5


ENVIRONMENT = {
    "version": "21.4R3-S5.4",
    "model": "ex4600-40f",
    "re_loads": {
        "re0": {
            "cpu_idle": "90",
            "memory_dram_size": "2048 MB",
            "memory_buffer_utilization": "25",
            "uptime": 86400,
            "last_reboot_reason": "Router rebooted after a normal shutdown.",
        }
    },
    "Temp": {"CPU": {"status": "OK", "temperature": 41}},
    "Fans": {"Fan 1": {"status": "OK"}, "Fan 2": {"status": "Failed"}},
    "Power": {"PSU 0": {"status": "OK"}},
}


def test_environment_metrics():
    data = collect(EnvironmentCollector(device(get_environment=ENVIRONMENT)))
    assert data[("pyez_junos_device_uptime_seconds", (("routing_engine", "re0"),))] == 86400
    assert data[("pyez_junos_device_fan_status", (("sensorname", "Fan 2"),))] == 0
    assert data[("pyez_junos_device_power_status", (("sensorname", "PSU 0"),))] == 1
    assert data[("pyez_junos_device_temp_celsius", (("sensorname", "CPU"),))] == 41
    assert data[("pyez_junos_device_temp_status", (("sensorname", "CPU"),))] == 1
    assert data[("pyez_junos_device_cpu_usage_ratio", (("cpu", "re0"),))] == 10
    assert data[("pyez_junos_device_ram_bytes_total", (("routing_engine", "re0"),))] == 2048 * 1049000
    assert (
        data[("pyez_junos_device_reboot_status", (("reboot_reason", "Router rebooted after a normal shutdown."),))] == 1
    )
    assert data[("pyez_junos_device_software_version_info", (("software_version", "21.4R3-S5.4"),))] == 1
    assert data[("pyez_junos_device_hardware_model_info", (("hardware_model", "ex4600-40f"),))] == 1
