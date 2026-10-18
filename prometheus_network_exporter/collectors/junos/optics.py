from __future__ import annotations

import yaml
from importlib.resources import read_text

from prometheus_client.core import GaugeMetricFamily

from ...config.junos import JunosMetricConfiguration
from ...devices import junosdevice
from ...utitlities import create_list_from_dict, merge_dicts_by_key
from ..base import Collector
from .. import junos
from . import base
from .rpcs import RPCS
from .xmlutil import iter_items, text


class OpticsCollector(Collector):
    default = yaml.load(read_text(junos, "optics.yaml"), Loader=yaml.SafeLoader)
    name = "interface"
    base_name = "{0}_{1}".format(base, name)

    def __init__(
        self,
        device: junosdevice.JuniperNetworkDevice,
        interface_regex: str = None,
        config_path: str = None,
    ) -> OpticsCollector:
        self.interface_regex = interface_regex
        config = self.default
        if config_path is not None:
            with open(config_path, "r") as file:
                config = yaml.load(file, Loader=yaml.SafeLoader)
        super(OpticsCollector, self).__init__(self.base_name, device, config)
        self._init_prometheus_metrics(metric_configuration=JunosMetricConfiguration)

    def collect(self, interfaces: dict, access: bool = False):
        assert isinstance(self.device, junosdevice.JuniperNetworkDevice)
        optics = (
            self.device.get_optics(interface_regex=self.interface_regex)
            if access
            else self.device.get_optics()
        )
        interfaces_optics_dict = merge_dicts_by_key(interfaces, optics)
        interfaces_optics_list = create_list_from_dict(
            interfaces_optics_dict, "interface_name"
        )
        for prometheus in self.prometheus_metrics.values():
            assert isinstance(prometheus, JunosMetricConfiguration)
            for interface in interfaces_optics_list:
                prometheus.metric.add_metric(
                    labels=self.get_labels(interface),
                    value=prometheus.function(interface.get(prometheus.json_key)),
                )
            yield prometheus.metric
            prometheus.flush()
        yield self.alarm_flags(interfaces_optics_list)

    def alarm_flags(self, interfaces: list) -> GaugeMetricFamily:
        """One sample per alarm or warning flag the transceiver reports.

        Read from the same RPC reply as the values above, so the transceiver
        is not polled a second time.
        """
        flags = GaugeMetricFamily(
            f"{self.base_name}_optics_alarm",
            "1 while the transceiver raises the alarm or warning flag",
            labels=["interface", "alarm"],
        )
        for interface in interfaces:
            for key, value in sorted(interface.items()):
                if not key.startswith("flag_") or value is None:
                    continue
                flags.add_metric(
                    [str(interface.get("interface_name")), key[len("flag_"):]],
                    1.0 if str(value).strip().lower() == "on" else 0.0,
                )
        return flags


class StandaloneOpticsCollector(OpticsCollector):
    """Optics without the interface collector in the same module.

    The optic metrics carry the labels description, MAC, speed and interface,
    which the legacy collector takes from its expensive ``show interfaces
    detail`` call. This variant reads them from plain ``show interfaces``, so
    the optics can move into a slow module with identical series.
    """

    INTERFACES = "[efgx][et]-*"

    def collect(self, interfaces: dict = None, access: bool = False):
        command, args = RPCS["interfaces_brief"]
        reply = self.device.rpc_reply(command, **args, interface_name=self.INTERFACES)
        interfaces = {}
        if reply is not None:
            for interface in iter_items(reply, ("physical-interface",)):
                name = text(interface, "name")
                if name is None:
                    continue
                interfaces[name] = {
                    "description": text(interface, "description"),
                    "macaddr": text(interface, "current-physical-address"),
                    "speed": text(interface, "speed"),
                }
        yield from super().collect(interfaces, access=access)
