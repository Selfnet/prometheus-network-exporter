from __future__ import annotations

import yaml
from importlib.resources import read_text
from ...config.junos import JunosMetricConfiguration, OSPFType
from ...devices import junosdevice
from ...utitlities import (
    create_list_from_dict,
    enrich_dict_from_upper_dict_by_labels,
    merge_dicts_by_key,
)
from .. import junos
from ..base import Collector
from . import base


class OSPFCollector(Collector):
    default = yaml.load(read_text(junos, "ospf.yaml"), Loader=yaml.SafeLoader)
    name = "interface_ospf"
    base_name = "{0}_{1}".format(base, name)

    def __init__(
        self,
        device: junosdevice.JuniperNetworkDevice,
        interface_regex: str = None,
        config_path: str = None,
    ) -> OSPFCollector:
        self.interface_regex = interface_regex
        config = self.default
        if config_path is not None:
            with open(config_path, "r") as file:
                config = yaml.load(file, Loader=yaml.SafeLoader)
        super(OSPFCollector, self).__init__(
            self.base_name, device=device, config=config
        )
        self._init_prometheus_metrics(metric_configuration=JunosMetricConfiguration)

    def collect(self, interfaces: dict, access: bool = False):
        assert isinstance(self.device, junosdevice.JuniperNetworkDevice)
        ospf = (
            self.device.get_ospf(interface_regex=self.interface_regex)
            if access
            else self.device.get_ospf()
        )
        interfaces_ospf_dict = merge_dicts_by_key(interfaces, ospf)
        interfaces_ospf_list = create_list_from_dict(
            interfaces_ospf_dict, "interface_name"
        )
        interfaces_ospf_enriched_list = enrich_dict_from_upper_dict_by_labels(
            interfaces_ospf_list, self.labels, OSPFType.OSPF.value
        )
        for prometheus in self.prometheus_metrics.values():
            assert isinstance(prometheus, JunosMetricConfiguration)
            for interface in interfaces_ospf_enriched_list:
                for ospf_interface in interface.get(OSPFType.OSPF.value, []):
                    prometheus.metric.add_metric(
                        labels=self.get_labels(ospf_interface),
                        value=prometheus.function(
                            ospf_interface.get(prometheus.json_key)
                        ),
                    )
            yield prometheus.metric
            prometheus.flush()
