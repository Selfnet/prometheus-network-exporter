
from __future__ import annotations

import yaml
from importlib_resources import read_text


from ...config.junos import JunosMetricConfiguration
from ...devices import junosdevice
from ..base import Collector
from .. import junos
from . import base


class EnvironmentCollector(Collector):
    default = yaml.load(
        read_text(
            junos,
            'environment.yaml'
        ),
        Loader=yaml.SafeLoader
    )
    name = 'device'
    base_name = "{0}_{1}".format(base, name)

    def __init__(
            self,
            device: junosdevice.JuniperNetworkDevice,
            config_path: str = None
    ) -> 'EnvironmentCollector':

        config = self.default
        if config_path is not None:
            with open(config_path, 'r') as file:
                config = yaml.load(file, loader=yaml.SafeLoader)

        super(EnvironmentCollector, self).__init__(self.base_name, device, config)
        self._init_prometheus_metrics(metric_configuration=JunosMetricConfiguration)
