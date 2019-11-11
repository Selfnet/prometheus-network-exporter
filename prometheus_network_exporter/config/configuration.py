from __future__ import annotations

from enum import Enum
from typing import Union, List

from cached_property import cached_property
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily
from prometheus_client.core import Metric as PrometheusMetric


class _Configuration(object):
    def __init__(self, config: dict):
        self._config = config


class Metric(Enum):
    Counter = 'counter'
    Gauge = 'gauge'
    Summary = 'summary'
    Histogram = 'histogram'
    Info = 'info'


class MetricConfiguration(_Configuration):

    metric_family = {
        Metric.Counter: CounterMetricFamily,
        Metric.Gauge: GaugeMetricFamily
    }

    def __init__(
        self,
        base_name: str,
        metric_type: Union[str, Metric],
        labels: List[LabelConfiguration],
        config: dict
    ) -> MetricConfiguration:
        self.__metric_type = metric_type if isinstance(metric_type, Metric) else Metric(metric_type.lower())
        self.__base_name = base_name
        super.__init__(MetricConfiguration, self).__init__(config=config)
        self.metric(
            self.base_name,
            self.description,
            labels=[label.label for label in labels]
        )

    @cached_property
    def base_name(self) -> str:
        if self._config.get('type') is None:
            return "{0}_{1}".format(
                self.__base_name,
                self._config['metric']
            )
        return "{0}_{1}_{2}".format(
            self.__base_name,
            self._config['metric'],
            self._config['type']
        )

    @property
    def description(self) -> str:
        return self._config['description']

    @property
    def metric(self) -> PrometheusMetric:
        return self.metric_family[self.__metric_type]

    @property
    def json_key(self) -> str:
        return self._config['key']


class LabelConfiguration(_Configuration):
    def __init__(self, config: dict):
        self._config = config
        super.__init__(LabelConfiguration, self).__init__(config=config)

    @property
    def label(self) -> str:
        return self._config['label']

    @property
    def json_key(self) -> str:
        return self._config['key']

    def get_label(self, data: dict) -> dict:
        return {
            self.label: self.data.get(self.json_key)
        }
