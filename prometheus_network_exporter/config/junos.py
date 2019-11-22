from __future__ import annotations
from typing import Callable
from .configuration import MetricConfiguration
from enum import Enum
from .functions import junos


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
        # Functions with simple type conversion.
        Function.IS_OK: junos.is_ok,
        Function.FLOATIFY: junos.floatify,
        Function.NONE_TO_ZERO: junos.none_to_zero,
        Function.NONE_TO_MINUS_INF: junos.none_to_minus_inf,
        Function.NONE_TO_PLUS_INF: junos.none_to_plus_inf,
        # Functions for complex Metrics
        Function.FAN_POWER_TEMP_STATUS: junos.fan_power_temp_status,
        Function.TEMP_CELSIUS: junos.temp_celsius,
        Function.REBOOT: junos.reboot,
        Function.CPU_IDLE: junos.cpu_idle,
        Function.CPU_USAGE: junos.cpu_usage,
        Function.RAM: junos.ram,
        Function.RAM_USAGE: junos.ram_usage,
        # The default function
        Function.DEFAULT: junos.default
    }

    @property
    def function(self) -> Callable:
        return self.function_mapping[
            Function(self.config.get('function'))
        ]

    @property
    def complex(self) -> bool:
        return self.config.get('complex', False)
