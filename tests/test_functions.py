"""Value conversions of the YAML driven collectors and the shared helpers."""

import math
from unittest import mock

import pytest

from prometheus_network_exporter import utitlities
from prometheus_network_exporter.config.configuration import LabelConfiguration
from prometheus_network_exporter.config.functions import junos
from prometheus_network_exporter.config.junos import JunosMetricConfiguration


def metric(function, metric_type="Gauge"):
    return JunosMetricConfiguration(
        base_name="pyez_junos_device",
        metric_type=metric_type,
        labels=[],
        config={"metric": "x", "key": "x", "description": "x", "function": function, "complex": True},
    )


def by_label(family, label):
    return {sample.labels[label]: sample.value for sample in family.samples}


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, 0),
        ("3", 3.0),
        (2, 2.0),
        (["7", "8"], 7.0),
    ],
)
def test_default(value, expected):
    assert junos.default(value) == expected
    assert junos.none_to_zero(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, 1.0),
        (False, 0.0),
        ("Up", 1.0),
        (" ok ", 1.0),
        ("Established", 1.0),
        ("down", 0.0),
        (None, 0.0),
    ],
)
def test_is_ok(value, expected):
    assert junos.is_ok(value) == expected


def test_is_ok_rejects_unknown_types():
    with pytest.raises(Exception):
        junos.is_ok(1)


def test_boolify():
    assert junos.boolify("True") is True
    assert junos.boolify("false") is False


def test_sum_values():
    assert junos.sum_values(["1", None, "2.5"]) == 3.5
    assert junos.sum_values("4") == 4.0
    assert junos.sum_values(None) == 0


def test_inf_defaults():
    assert junos.none_to_minus_inf(None) == -math.inf
    assert junos.none_to_minus_inf(3) == 3
    assert junos.none_to_plus_inf(None) == math.inf
    assert junos.none_to_plus_inf(3) == 3


@pytest.mark.parametrize(
    "value, expected",
    [
        ("- Inf", -math.inf),
        ("Inf", math.inf),
        ("-2.5", -2.5),
        (1, 1.0),
        (None, 0),
    ],
)
def test_floatify(value, expected):
    assert junos.floatify(value) == expected


def test_fan_power_temp_status():
    data = {"FPC 0 Fan 1": {"status": "OK"}, "PSU 1": {"status": "Failed"}}
    family = junos.fan_power_temp_status(metric("fan_power_temp_status"), data)
    assert by_label(family, "sensorname") == {"FPC 0 Fan 1": 1.0, "PSU 1": 0.0}


def test_temp_celsius_marks_missing_readings():
    data = {"CPU": {"temperature": 45}, "Absent": {"temperature": None}}
    family = junos.temp_celsius(metric("temp_celsius"), data)
    assert by_label(family, "sensorname") == {"CPU": 45, "Absent": -math.inf}


@pytest.mark.parametrize(
    "reason, expected",
    [
        ("Router rebooted after a normal shutdown.", 1),
        ("0x2:watchdog failure", 0),
        ("kernel error", 0),
    ],
)
def test_reboot(reason, expected):
    family = junos.reboot(metric("reboot"), {"re0": {"last_reboot_reason": reason}})
    assert [sample.value for sample in family.samples] == [expected]
    assert family.samples[0].labels == {"reboot_reason": reason}


def test_cpu_usage_and_idle():
    data = {"0": {"cpu_idle": "93"}, "1": {"cpu_idle": None}}
    assert by_label(junos.cpu_usage(metric("cpu_usage"), data), "cpu") == {"0": 7, "1": 100}
    assert by_label(junos.cpu_idle(metric("cpu_idle"), {"0": {"cpu_idle": "93"}}), "cpu") == {"0": 93}


def test_memory_and_uptime():
    data = {"re0": {"memory_dram_size": "2048 MB", "memory_buffer_utilization": "50", "uptime": 3600}}
    assert by_label(junos.ram(metric("ram"), data), "routing_engine") == {"re0": 2048 * 1049000}
    assert by_label(junos.ram_usage(metric("ram_usage"), data), "routing_engine") == {"re0": 1024 * 1049000}
    assert by_label(junos.uptime(metric("uptime"), data), "routing_engine") == {"re0": 3600}


def test_merge_and_list_helpers():
    merged = utitlities.merge_dicts_by_key({"a": {"x": 1}, "b": {"x": 2}}, {"a": {"y": 3}, "c": {"y": 4}})
    assert merged == {"a": {"x": 1, "y": 3}, "b": {"x": 2}}
    assert utitlities.create_list_from_dict({"a": {"x": 1}}, "name", "if-{}") == [{"name": "if-a", "x": 1}]
    assert utitlities.remove_empty({"a": None, "b": "None", "c": "", "d": 0, "e": "x"}) == {"d": 0, "e": "x"}


def test_enrich_from_upper_dict():
    labels = [LabelConfiguration(config={"label": "area", "key": "area"})]
    listing = [
        {"area": "0.0.0.0", "neighbors": [{"id": "a"}, {"id": "b"}]},
        {"area": "", "neighbors": [{"id": "c"}]},
        {"area": "0.0.0.1"},
    ]
    result = utitlities.enrich_dict_from_upper_dict_by_labels(listing, labels, "neighbors")
    assert result[0]["neighbors"] == [{"id": "a", "area": "0.0.0.0"}, {"id": "b", "area": "0.0.0.0"}]
    assert result[1]["neighbors"] == [{"id": "c"}]
    assert "neighbors" not in result[2]


def test_flatten():
    assert utitlities.flatten({"a": {"b": {"c": 1}, "d": 2}, "e": 3}) == {"a_b_c": 1, "a_d": 2, "e": 3}
    assert utitlities.flatten({"a": {"b": 1}}, sep=".") == {"a.b": 1}


def test_timed_cache_expires():
    calls = []

    @utitlities.timed_cache(seconds=60, maxsize=4)
    def lookup(value):
        calls.append(value)
        return value * 2

    assert lookup(2) == 4
    assert lookup(2) == 4
    assert calls == [2]
    assert lookup.cache_info().hits == 1
    later = utitlities.datetime.utcnow() + utitlities.timedelta(seconds=61)
    with mock.patch.object(utitlities, "datetime") as clock:
        clock.utcnow.return_value = later
        assert lookup(2) == 4
    assert calls == [2, 2]
    lookup.cache_clear()
    assert lookup.cache_info().currsize == 0
