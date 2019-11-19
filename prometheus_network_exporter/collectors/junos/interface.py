
from __future__ import annotations

import yaml
from importlib_resources import read_text

from ...config.junos import JunosMetricConfiguration
from ...devices import junosdevice
from ...utitlities import create_list_from_dict
from .. import junos
from ..base import Collector
from . import base
from .optics import OpticsCollector
from .ospf import OSPFCollector
from .ospf3 import OSPF3Collector


class InterfaceCollector(Collector):
    default = yaml.load(
        read_text(
            junos,
            'interface.yaml'
        ),
        Loader=yaml.SafeLoader
    )
    name = 'interface'
    interface_regex = '[gxe][et]-*/1/*'
    base_name = "{0}_{1}".format(base, name)

    def __init__(
            self,
            device: junosdevice.JuniperNetworkDevice,
            access: bool = False,
            ospf: bool = False,
            optics: bool = False,
            config_path: str = None
    ) -> InterfaceCollector:
        self.access = access
        self.collectors = []
        config = self.default
        if config_path is not None:
            with open(config_path, 'r') as file:
                config = yaml.load(file, loader=yaml.SafeLoader)
        super(InterfaceCollector, self).__init__(self.base_name, device, config=config)
        self._init_prometheus_metrics(metric_configuration=JunosMetricConfiguration)
        if ospf:
            self.collectors.append(OSPFCollector(self.device))
            self.collectors.append(OSPF3Collector(self.device))

        if optics:
            self.collectors.append(OpticsCollector(self.device))

    def collect(self):
        assert isinstance(self.device, junosdevice.JuniperNetworkDevice)
        interfaces_dict = self.device.get_interfaces(
            interface_regex=self.interface_regex
        ) if self.access else self.device.get_interfaces()
        interfaces_list = create_list_from_dict(interfaces_dict, 'interface_name')
        for collector in self.collectors:
            for metric in collector.collect(interfaces_dict, access=self.access):
                yield metric

        for prometheus in self.prometheus_metrics.values():
            assert isinstance(prometheus, JunosMetricConfiguration)
            for interface in interfaces_list:
                prometheus.metric.add_metric(
                    labels=self.get_labels(interface),
                    value=interface.get(
                        prometheus.json_key
                    )
                )
            yield prometheus.metric
