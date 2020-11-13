from __future__ import annotations

import ipaddress

import yaml
from cached_property import cached_property
from importlib.resources import read_text

from ...config.junos import JunosMetricConfiguration
from ...devices import junosdevice
from .. import junos
from ..base import Collector
from . import base


class IGMPCollector(Collector):
    default = yaml.load(
        read_text(
            junos,
            'igmp.yaml'
        ),
        Loader=yaml.SafeLoader
    )
    name = 'igmp'
    base_name = "{0}_{1}".format(base, name)

    def __init__(
            self,
            device: junosdevice.JuniperNetworkDevice,
            config_path: str = None) -> IGMPCollector:
        config = self.default
        if config_path is not None:
            with open(config_path, 'r') as file:
                config = yaml.load(file, Loader=yaml.SafeLoader)
        super(IGMPCollector, self).__init__(self.base_name, device, config)
        self._init_prometheus_metrics(metric_configuration=JunosMetricConfiguration)

    @cached_property
    def allowed_networks(self):
        return [
            ipaddress.ip_network(
                prefix
            ) for prefix in self.config['IGMP_NETWORKS'].get('allow', {}).keys()
        ]

    @cached_property
    def ignored_networks(self):
        return [
            ipaddress.ip_network(
                net
            ) for net in self.config['IGMP_NETWORKS'].get('ignore', {}).keys()
        ]

    def get_igmp_broadcasts(self):
        igmp = self.device.get_igmp()
        counter = {}

        for broadcaster in self.config['IGMP_NETWORKS']['allow'].values():
            counter[broadcaster] = 0

        for network in self.allowed_networks:
            for mgm_addresses in igmp.values():
                for address in mgm_addresses['mgm_addresses']:
                    current_addr = ipaddress.ip_address(address)
                    if current_addr in network:
                        for ignore in self.ignored_networks:
                            if current_addr not in ignore:
                                counter[self.config['IGMP_NETWORKS']['allow']
                                        [str(network)]] += 1
        return [
            {
                "broadcaster": broadcaster,
                "broadcasts": broadcasts
            } for broadcaster, broadcasts in counter.items()
        ]

    def collect(self):
        igmp_list = self.get_igmp_broadcasts()
        for prometheus in self.prometheus_metrics.values():
            for interface in igmp_list:
                prometheus.metric.add_metric(
                    labels=self.get_labels(interface),
                    value=prometheus.function(
                        interface.get(
                            prometheus.json_key
                        )
                    )
                )
            yield prometheus.metric
            prometheus.flush()
