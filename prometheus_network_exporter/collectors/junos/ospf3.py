from __future__ import annotations

import yaml
from importlib_resources import read_text

from ...config.junos import JunosMetricConfiguration, OSPFType
from ...devices import junosdevice
from ...utitlities import (create_list_from_dict,
                           enrich_dict_from_upper_dict_by_labels,
                           merge_dicts_by_key)
from .. import junos
from ..base import Collector
from . import base


class OSPF3Collector(Collector):
    default = yaml.load(
        read_text(
            junos,
            'ospf.yaml'
        ),
        Loader=yaml.SafeLoader
    )
    name = 'interface_ospf3'
    base_name = "{0}_{1}".format(base, name)

    def __init__(
            self,
            device: junosdevice.JuniperNetworkDevice,
            interface_regex: str = None,
            config_path: str = None) -> OSPF3Collector:
        self.interface_regex = interface_regex
        config = self.default
        if config_path is not None:
            with open(config_path, 'r') as file:
                config = yaml.load(file, loader=yaml.SafeLoader)
        super(OSPF3Collector, self).__init__(self.base_name, device, config)
        self._init_prometheus_metrics(metric_configuration=JunosMetricConfiguration)

    def collect(self, interfaces: dict, access: bool = False):
        assert isinstance(self.device, junosdevice.JuniperNetworkDevice)
        ospf3 = self.device.get_ospf3(
            interface_regex=self.interface_regex
        ) if access else self.device.get_ospf3()
        interfaces_ospf3_dict = merge_dicts_by_key(interfaces, ospf3)
        interfaces_ospf3_list = create_list_from_dict(interfaces_ospf3_dict, 'interface_name')
        interfaces_ospf3_enriched_list = enrich_dict_from_upper_dict_by_labels(
            interfaces_ospf3_list,
            self.labels,
            OSPFType.OSPF3.value
        )
        for prometheus in self.prometheus_metrics.values():
            assert isinstance(prometheus, JunosMetricConfiguration)
            for interface in interfaces_ospf3_enriched_list:
                for ospf3_interface in interface.get(OSPFType.OSPF3.value, []):
                    prometheus.metric.add_metric(
                        labels=self.get_labels(ospf3_interface),
                        value=prometheus.function(
                            ospf3_interface.get(
                                prometheus.json_key
                            )
                        )
                    )
            yield prometheus.metric
