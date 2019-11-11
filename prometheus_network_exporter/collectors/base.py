from prometheus_network_exporter.devices.basedevice import Device
from prometheus_network_exporter.config.configuration import LabelConfiguration
from prometheus_network_exporter.config.junos import JunosMetricConfiguration
from prometheus_network_exporter.config.junos import


class Collector(object):

    def __init__(self, base_name: str, device: Device, config: dict):
        self.base_name = base_name
        self.device = device
        self.config = config
        self.prometheus_metrics = {}
        self.labels = []

    def _init_prometheus_metrics(self, label_config_key='LABELS', metric_config_key='METRICS') -> dict:
        for label in self.config.get(label_config_key, [{}]):
            self.labels.append(LabelConfiguration(label_config_key))

        for metric_type, possible_metrics in self.config.get(metric_config_key, {}).items():
            for possible_metric in possible_metrics:
                prometheus_metric = JunosMetricConfiguration(
                    self.base_name,
                    metric_type=metric_type,
                    config=possible_metric
                )
                self.prometheus_metrics[prometheus_metric.base_name] = prometheus_metric

    def collect(self):
        raise NotImplementedError
