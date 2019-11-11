from __future__ import annotations
from typing import Callable
from .configuration import MetricConfiguration
from enum import Enum
from .definitions.junos import functions


class Function(Enum):
    IS_OK = 'is_ok'
    FLOATIFY = 'floatify'
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
        Function.FAN_POWER_TEMP_STATUS: functions.fan_power_temp_status,
        Function.TEMP_CELSIUS: functions.temp_celsius,
        Function.REBOOT: functions.reboot,
        Function.CPU_IDLE: functions.cpu_idle,
        Function.CPU_USAGE: functions.cpu_usage,
        Function.RAM: functions.ram,
        Function.RAM_USAGE: functions.ram_usage,
        Function.DEFAULT: functions.default
    }

    def __init__(self, *args, **kwargs) -> JunosMetricConfiguration:
        super(JunosMetricConfiguration, self).__init__(*args, **kwargs)

    @property
    def function(self) -> Callable:
        return self.function_mapping(
            Function(self._config.get('function'))
        )
