from typing import Union
import logging
from ...utitlities import create_list_from_dict
from ..configuration import LabelConfiguration, MetricConfiguration


def default(value) -> float:
    if isinstance(value, list):
        return default(value[0])
    return 0 if value is None else float(value)


def is_ok(boolean: Union[bool, str]) -> float:
    if isinstance(boolean, bool):
        if boolean:
            return 1.0
        return 0.0
    elif isinstance(boolean, str):
        if boolean.lower().strip() in ["up", "ok", "established"]:
            return 1.0
        return 0.0
    elif boolean is None:
        return 0.0
    else:
        raise Exception("Unknown Type: {}".format(boolean))


def boolify(string: str) -> bool:
    return "true" in string.lower()


def none_to_zero(string) -> float:
    return default(string)


def none_to_minus_inf(string) -> float:
    return -float("inf") if string is None else string


def none_to_plus_inf(string) -> float:
    return float("inf") if string is None else string


def floatify(string: Union[str, float]) -> float:
    if isinstance(string, str):
        if "- Inf" in string:
            return -float("inf")
        elif "Inf" in string:
            return float("inf")
    return float(string) if string is not None else none_to_zero(string)


# The complex Functions


def fan_power_temp_status(prometheus: MetricConfiguration, data: dict):
    prometheus.labels = [
        LabelConfiguration(config={"label": "sensorname", "key": "sensorname"})
    ]
    prometheus.metric = prometheus.build_metric()
    data_list = create_list_from_dict(data, "sensorname")
    for data_part in data_list:
        prometheus.metric.add_metric(
            labels=[label.get_label(data_part) for label in prometheus.labels],
            value=is_ok(data_part.get("status")),
        )
    return prometheus.metric


def temp_celsius(prometheus: MetricConfiguration, data: dict):
    prometheus.labels = [
        LabelConfiguration(config={"label": "sensorname", "key": "sensorname"})
    ]
    prometheus.metric = prometheus.build_metric()
    data_list = create_list_from_dict(data, "sensorname")
    for data_part in data_list:
        prometheus.metric.add_metric(
            labels=[label.get_label(data_part) for label in prometheus.labels],
            value=data_part.get("temperature") or float("-inf"),
        )
    return prometheus.metric


def reboot(prometheus: MetricConfiguration, data: dict):
    data = list(data.values())[0]
    label_config = LabelConfiguration(
        config={"label": "reboot_reason", "key": "last_reboot_reason"}
    )
    reason_string = label_config.get_label(data)
    prometheus.labels = [label_config]
    prometheus.metric = prometheus.build_metric()
    reason = 1
    for a in ["failure", "error", "failed"]:
        if a in reason_string.lower():
            reason = 0
    prometheus.metric.add_metric(
        labels=[label.get_label(data) for label in prometheus.labels], value=reason
    )
    return prometheus.metric


def cpu_usage(prometheus: MetricConfiguration, data: dict):
    prometheus.labels = [LabelConfiguration(config={"label": "cpu", "key": "cpu"})]
    prometheus.metric = prometheus.build_metric()
    data_list = create_list_from_dict(data, "cpu")
    for perf in data_list:
        prometheus.metric.add_metric(
            labels=[label.get_label(perf) for label in prometheus.labels],
            value=(100 - int(perf["cpu_idle"] or 0)),
        )
    return prometheus.metric


def cpu_idle(prometheus: MetricConfiguration, data: dict):
    prometheus.labels = [LabelConfiguration(config={"label": "cpu", "key": "cpu"})]
    prometheus.metric = prometheus.build_metric()
    data_list = create_list_from_dict(data, "cpu")
    for perf in data_list:
        prometheus.metric.add_metric(
            labels=[label.get_label(perf) for label in prometheus.labels],
            value=int(perf["cpu_idle"]),
        )
    return prometheus.metric


def ram_usage(prometheus: MetricConfiguration, data: dict):
    prometheus.labels = [
        LabelConfiguration(config={"label": "routing_engine", "key": "routing_engine"})
    ]
    prometheus.metric = prometheus.build_metric()
    data_list = create_list_from_dict(data, "routing_engine")
    for perf in data_list:
        memory_complete = perf["memory_dram_size"].lower().replace("mb", "").strip()
        memory_complete = int(memory_complete)
        memory_usage = int(perf["memory_buffer_utilization"])
        memory_bytes_usage = (memory_complete * memory_usage / 100) * 1049000
        prometheus.metric.add_metric(
            labels=[label.get_label(perf) for label in prometheus.labels],
            value=memory_bytes_usage,
        )
    return prometheus.metric


def uptime(prometheus: MetricConfiguration, data: dict):
    prometheus.labels = [
        LabelConfiguration(config={"label": "routing_engine", "key": "routing_engine"})
    ]
    prometheus.metric = prometheus.build_metric()
    data_list = create_list_from_dict(data, "routing_engine")
    for perf in data_list:
        prometheus.metric.add_metric(
            labels=[label.get_label(perf) for label in prometheus.labels],
            value=perf["uptime"],
        )
    return prometheus.metric


def ram(prometheus: MetricConfiguration, data: dict):
    prometheus.labels = [
        LabelConfiguration(config={"label": "routing_engine", "key": "routing_engine"})
    ]
    prometheus.metric = prometheus.build_metric()
    data_list = create_list_from_dict(data, "routing_engine")
    for perf in data_list:
        memory_complete = perf["memory_dram_size"].lower().replace("mb", "").strip()
        memory_complete = int(memory_complete)
        memory_bytes = memory_complete * 1049000
        prometheus.metric.add_metric(
            labels=[label.get_label(perf) for label in prometheus.labels],
            value=memory_bytes,
        )
    return prometheus.metric
