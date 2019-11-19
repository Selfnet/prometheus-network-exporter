from __future__ import annotations

import yaml
from importlib_resources import read_text

from ...config.junos import JunosMetricConfiguration
from ...devices import junosdevice
from ...utitlities import create_list_from_dict
from .. import junos
from ..base import Collector
from . import base


class BGPCollector(Collector):

    default = yaml.load(
        read_text(
            junos,
            'bgp.yaml'
        ),
        Loader=yaml.SafeLoader
    )
    name = 'bgp'
    base_name = "{0}_{1}".format(base, name)

    def __init__(
        self,
        device: junosdevice.JuniperNetworkDevice,
        config_path: str = None
    ) -> 'BGPCollector':
        config = self.default
        if config_path is not None:
            with open(config_path, 'r') as file:
                config = yaml.load(file, loader=yaml.SafeLoader)

        super(BGPCollector, self).__init__(self.base_name, device, config)
        self._init_prometheus_metrics(metric_configuration=JunosMetricConfiguration)

    def collect(self):
        bgp = junosdevice.JuniperNetworkDevice(self.device).get_bgp()

        if bgp:
            bgp_list = create_list_from_dict(bgp, 'peeraddr')
            for prometheus in self.prometheus_metrics.values():
                prometheus = JunosMetricConfiguration(prometheus)
                for interface in bgp_list:
                    labels = self.get_labels(interface)
                    prometheus.metric.add_metric(
                        labels,
                        prometheus.function(
                            interface.get(
                                prometheus.json_key
                            )
                        )
                    )
                yield prometheus.metric
