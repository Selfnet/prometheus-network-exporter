"""Custom YAML controls the fields and labels of the legacy collectors."""

from unittest.mock import Mock

import pytest
import yaml

from prometheus_network_exporter.collectors.junos.bgp import BGPCollector
from prometheus_network_exporter.collectors.junos.interface import InterfaceCollector
from prometheus_network_exporter.collectors.junos.optics import OpticsCollector
from prometheus_network_exporter.collectors.junos.ospf import OSPFCollector
from prometheus_network_exporter.collectors.junos.ospf3 import OSPF3Collector
from prometheus_network_exporter.devices.junosdevice import JuniperNetworkDevice


@pytest.mark.parametrize(
    "collector_type", [BGPCollector, InterfaceCollector, OpticsCollector, OSPFCollector, OSPF3Collector]
)
def test_custom_metric_fields_labels_and_repeated_scrapes(tmp_path, collector_type):
    config = tmp_path / "metrics.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "LABELS": [{"label": "custom_label", "key": "description"}],
                "METRICS": {"Gauge": [{"metric": "custom", "key": "reading", "description": "Custom reading"}]},
            }
        )
    )
    device = Mock(spec=JuniperNetworkDevice)
    reading = {"reading": 12.5, "description": "uplink"}
    device.get_bgp.return_value = {"192.0.2.1": reading}
    device.get_interfaces.return_value = {"ae0": reading}
    device.get_optics.return_value = {"ae0": reading}
    device.get_ospf.return_value = {"ae0": {"ospf": [reading]}}
    device.get_ospf3.return_value = {"ae0": {"ospf3": [reading]}}
    collector = collector_type(device, config_path=str(config))

    def collect():
        families = (
            collector.collect()
            if collector_type in (BGPCollector, InterfaceCollector)
            else collector.collect({"ae0": {}})
        )
        return [(s.name, s.labels, s.value) for family in families for s in family.samples]

    assert collect() == [(f"{collector.base_name}_custom", {"custom_label": "uplink"}, 12.5)]
    reading["reading"] = 7
    assert collect() == [(f"{collector.base_name}_custom", {"custom_label": "uplink"}, 7)]
