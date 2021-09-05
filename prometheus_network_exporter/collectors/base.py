from prometheus_network_exporter.devices.basedevice import Device
from prometheus_network_exporter.config.configuration import LabelConfiguration
from prometheus_network_exporter.config.configuration import MetricConfiguration

from typing import Dict, List


class Collector(object):
    def __init__(self, base_name: str, device: Device, config: dict):
        self.base_name = base_name
        self.device = device
        self.config = config
        self.prometheus_metrics: Dict[str, MetricConfiguration] = {}
        self.labels: List[LabelConfiguration] = []

    def get_labels(self, dictionary: dict) -> tuple:
        temp = []
        for label in self.labels:
            temp.append(label.get_label(dictionary))
        return tuple(temp)

    def _init_prometheus_metrics(
        self,
        label_config_key="LABELS",
        metric_config_key="METRICS",
        metric_configuration: MetricConfiguration = MetricConfiguration,
    ):
        for label in self.config.get(label_config_key, []):
            self.labels.append(LabelConfiguration(config=label))

        for metric_type, possible_metrics in self.config.get(
            metric_config_key, {}
        ).items():
            for possible_metric in possible_metrics:
                prometheus_metric = metric_configuration(
                    base_name=self.base_name,
                    labels=self.labels,
                    metric_type=metric_type,
                    config=possible_metric,
                )
                self.prometheus_metrics[prometheus_metric.base_name] = prometheus_metric

    def collect(self):
        raise NotImplementedError
