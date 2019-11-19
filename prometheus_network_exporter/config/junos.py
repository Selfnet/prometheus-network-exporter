from __future__ import annotations
from typing import Callable
from .configuration import MetricConfiguration
from enum import Enum
from .definitions.junos import functions


class OSPFType(Enum):
    OSPF3 = 'ospf3'
    OSPF = 'ospf'


class Function(Enum):
    IS_OK = 'is_ok'
    FLOATIFY = 'floatify'
    NONE_TO_ZERO = 'none_to_zero'
    NONE_TO_MINUS_INF = 'none_to_minus_inf'
    NONE_TO_PLUS_INF = 'none_to_plus_inf'
    FAN_POWER_TEMP_STATUS = 'fan_power_temp_status'
    TEMP_CELSIUS = 'temp_celsius'
    REBOOT = 'reboot'
    CPU_IDLE = 'cpu_idle'
    CPU_USAGE = 'cpu_usage'
    RAM = 'ram'
    RAM_USAGE = 'ram_usage'
    DEFAULT = None


class JunosMetricConfiguration(MetricConfiguration):

    function_mapping = {
        Function.IS_OK: functions.is_ok,
        Function.FLOATIFY: functions.floatify,
        Function.NONE_TO_ZERO: functions.none_to_zero,
        Function.NONE_TO_MINUS_INF: functions.none_to_minus_inf,
        Function.NONE_TO_PLUS_INF: functions.none_to_plus_inf,
        Function.FAN_POWER_TEMP_STATUS: functions.fan_power_temp_status,
        Function.TEMP_CELSIUS: functions.temp_celsius,
        Function.REBOOT: functions.reboot,
        Function.CPU_IDLE: functions.cpu_idle,
        Function.CPU_USAGE: functions.cpu_usage,
        Function.RAM: functions.ram,
        Function.RAM_USAGE: functions.ram_usage,
        Function.DEFAULT: functions.default
    }

    @property
    def function(self) -> Callable:
        return self.function_mapping[
            Function(self.config.get('function'))
        ]
