from __future__ import annotations

import yaml
from importlib_resources import read_text

from ...config.junos import JunosMetricConfiguration
from ...devices import junosdevice
from ...utitlities import create_list_from_dict, merge_dicts_by_key
from ..base import Collector
from .. import junos
from . import base


class OpticsCollector(Collector):
    default = yaml.load(
        read_text(
            junos,
            'optics.yaml'
        ),
        Loader=yaml.SafeLoader
    )
    name = 'interface'
    base_name = "{0}_{1}".format(base, name)

    def __init__(
            self,
            device: junosdevice.JuniperNetworkDevice,
            interface_regex: str = None,
            config_path: str = None) -> OpticsCollector:
        self.interface_regex = interface_regex
        config = self.default
        if config_path is not None:
            with open(config_path, 'r') as file:
                config = yaml.load(file, loader=yaml.SafeLoader)
        super(OpticsCollector, self).__init__(self.base_name, device, config)
        self._init_prometheus_metrics(metric_configuration=JunosMetricConfiguration)

    def collect(self, interfaces: dict, access: bool = False):
        assert isinstance(self.device, junosdevice.JuniperNetworkDevice)
        optics = self.device.get_optics(
            interface_regex=self.interface_regex
        ) if access else self.device.get_optics()
        interfaces_optics_dict = merge_dicts_by_key(interfaces, optics)
        interfaces_optics_list = create_list_from_dict(interfaces_optics_dict, 'interface_name')
        for prometheus in self.prometheus_metrics.values():
            assert isinstance(prometheus, JunosMetricConfiguration)
            for interface in interfaces_optics_list:
                prometheus.metric.add_metric(
                    labels=self.get_labels(interface),
                    value=prometheus.function(
                        interface.get(
                            prometheus.json_key
                        )
                    )
                )
            yield prometheus.metric
