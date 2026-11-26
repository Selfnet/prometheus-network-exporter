from __future__ import annotations

import yaml
from prometheus_client.core import InfoMetricFamily
from importlib.resources import read_text

from ...config.configuration import Metric, MetricConfiguration
from ...config.junos import JunosMetricConfiguration
from ...devices import junosdevice
from .. import junos
from ..base import Collector
from . import base


class EnvironmentCollector(Collector):
    default = yaml.load(read_text(junos, "environment.yaml"), Loader=yaml.SafeLoader)
    name = "device"
    base_name = "{0}_{1}".format(base, name)

    def __init__(self, device: junosdevice.JuniperNetworkDevice, config_path: str | None = None) -> None:

        config = self.default
        if config_path is not None:
            with open(config_path, "r") as file:
                config = yaml.load(file, Loader=yaml.SafeLoader)

        super(EnvironmentCollector, self).__init__(self.base_name, device, config)
        self._init_prometheus_metrics(metric_configuration=JunosMetricConfiguration)

    def collect_complex_metric(self, metric: MetricConfiguration, complex_data: dict) -> list:
        return metric.function(metric, complex_data)

    def collect(self):
        environment = self.device.get_environment()
        for prometheus in self.prometheus_metrics.values():
            if prometheus.complex:
                yield self.collect_complex_metric(prometheus, environment.get(prometheus.json_key))
            elif prometheus.metric_type is Metric.Info:
                prometheus.metric.add_metric(
                    labels=self.get_labels(environment),
                    value={prometheus.name: environment.get(prometheus.json_key, "")},
                )
                yield prometheus.metric
            else:
                prometheus.metric.add_metric(
                    labels=self.get_labels(environment),
                    value=prometheus.function(environment.get(prometheus.json_key)),
                )
                yield prometheus.metric
            prometheus.flush()
        if self.component_classes:
            yield self.environment_states(environment)

    @property
    def component_classes(self) -> list:
        """Environment classes whose reported state is exported; a config without the key exports none."""
        return list(self.config.get("COMPONENT_STATES") or [])

    def environment_states(self, environment: dict) -> InfoMetricFamily:
        metric = InfoMetricFamily(
            f"{self.base_name}_environment",
            "Reported component state; unknown means no status was supplied",
            labels=["component_class", "sensorname"],
        )
        for component_class in self.component_classes:
            for name, values in (environment.get(component_class) or {}).items():
                status = values.get("status")
                status = str(status).strip() if status is not None else ""
                metric.add_metric([component_class, name], {"status": status or "unknown"})
        return metric
