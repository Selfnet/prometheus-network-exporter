from __future__ import annotations

import ipaddress

import yaml
from cached_property import cached_property
from importlib_resources import read_text

from ...config.junos import JunosMetricConfiguration
from ...devices import junosdevice
from ...utitlities import create_list_from_dict, merge_dicts_by_key
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
            interface_regex: str = None,
            config_path: str = None) -> 'IGMPCollector':
        self.interface_regex = interface_regex
        config = self.default
        if config_path is not None:
            with open(config_path, 'r') as file:
                config = yaml.load(file, loader=yaml.SafeLoader)
        super(IGMPCollector, self).__init__(self.base_name, device, config)

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
        igmp = junosdevice.JuniperNetworkDevice(self.device).get_igmp()
        counter = {}
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
            prometheus = JunosMetricConfiguration(prometheus)
            for interface in igmp_list:
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
