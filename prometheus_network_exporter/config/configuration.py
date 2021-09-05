from __future__ import annotations

from enum import Enum
from typing import List, Union

from prometheus_client.core import (
    CounterMetricFamily,
    GaugeMetricFamily,
    InfoMetricFamily,
)
from prometheus_client.core import Metric as PrometheusMetric


class _Configuration(object):
    def __init__(self, config: dict):
        self.config = config


class Metric(Enum):
    Counter = "counter"
    Gauge = "gauge"
    Summary = "summary"
    Histogram = "histogram"
    Info = "info"


class LabelConfiguration(_Configuration):
    def __init__(self, config: dict):
        super(LabelConfiguration, self).__init__(config=config)

    @property
    def label(self) -> str:
        return self.config["label"]

    @property
    def json_key(self) -> str:
        return self.config["key"]

    def get_label(self, data: dict) -> Union[str, None]:
        return str(data.get(self.json_key))

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f"<label: {self.label}, key: {self.json_key}>"


class MetricConfiguration(_Configuration):

    metric_family = {
        Metric.Counter: CounterMetricFamily,
        Metric.Gauge: GaugeMetricFamily,
        Metric.Info: InfoMetricFamily,
    }

    def __init__(
        self,
        base_name: str,
        metric_type: Union[str, Metric],
        labels: List[LabelConfiguration],
        config: dict,
    ) -> MetricConfiguration:
        self.__metric_type = (
            metric_type
            if isinstance(metric_type, Metric)
            else Metric(metric_type.lower())
        )
        self.__base_name = base_name
        self.labels = labels
        super(MetricConfiguration, self).__init__(config=config)
        self.metric = self.build_metric()

    @property
    def base_name(self) -> str:
        if self.config.get("type") is None:
            return "{0}_{1}".format(self.__base_name, self.config["metric"])
        return "{0}_{1}_{2}".format(
            self.__base_name, self.config["metric"], self.config["type"]
        )

    @property
    def description(self) -> str:
        return self.config["description"]

    def build_metric(self) -> PrometheusMetric:
        return self.metric_family[self.__metric_type](
            self.base_name,
            self.description,
            labels=[label.label for label in self.labels],
        )

    def flush(self):
        self.metric.samples.clear()

    @property
    def metric_type(self) -> Metric:
        return self.__metric_type

    @property
    def name(self) -> str:
        return self.config["metric"]

    @property
    def json_key(self) -> str:
        return self.config["key"]
