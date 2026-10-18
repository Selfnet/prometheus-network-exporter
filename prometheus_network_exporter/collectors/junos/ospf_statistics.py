from __future__ import annotations

from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from ...devices import junosdevice
from ..base import Collector
from . import base


class OSPFStatisticsCollector(Collector):
    counter_fields = {
        "dbds_retransmit": "dbds-retransmit",
        "lsas_flooded": "lsas-flooded",
        "lsas_high_prio_flooded": "lsas-high-prio-flooded",
        "lsas_retransmit": "lsas-retransmit",
        "lsas_neighbor_transmitted": "lsas-nbr-transmit",
        "lsas_requested": "lsas-requested",
        "lsas_acknowledged": "lsas-acknowledged",
    }
    gauge_fields = {
        "flood_queue_depth": "flood-queue-depth",
        "retransmit_queue_entries": "total-retransmits",
        "database_summary_queue_entries": "total-database-summaries",
        "linkstate_request_queue_entries": "total-linkstate-request",
    }

    def __init__(
        self, device: junosdevice.JuniperNetworkDevice, protocol: str = "ospf"
    ):
        if protocol not in ("ospf", "ospf3"):
            raise ValueError(f"Unsupported OSPF protocol: {protocol}")
        self.protocol = protocol
        self.base_name = f"{base}_{protocol}"
        super().__init__(self.base_name, device, config={})

    @staticmethod
    def _number(element, field: str) -> float:
        value = element.findtext(f"{{*}}{field}")
        return float(value) if value is not None else 0.0

    def collect(self):
        statistics = getattr(self.device, f"get_{self.protocol}_statistics")()
        if statistics is None:
            return

        packets_sent = CounterMetricFamily(
            f"{self.base_name}_packets_sent",
            f"Total number of {self.protocol.upper()} packets sent",
            labels=["packet_type"],
        )
        packets_received = CounterMetricFamily(
            f"{self.base_name}_packets_received",
            f"Total number of {self.protocol.upper()} packets received",
            labels=["packet_type"],
        )
        for packet in statistics.findall("{*}packet-statistics"):
            packet_type = packet.findtext("{*}ospf-packet-type") or "unknown"
            packets_sent.add_metric(
                [packet_type], self._number(packet, "packets-sent")
            )
            packets_received.add_metric(
                [packet_type], self._number(packet, "packets-received")
            )
        yield packets_sent
        yield packets_received

        for metric_name, xml_field in self.counter_fields.items():
            metric = CounterMetricFamily(
                f"{self.base_name}_{metric_name}",
                f"Junos {self.protocol.upper()} statistic {xml_field}",
            )
            metric.add_metric([], self._number(statistics, xml_field))
            yield metric

        for metric_name, xml_field in self.gauge_fields.items():
            metric = GaugeMetricFamily(
                f"{self.base_name}_{metric_name}",
                f"Junos {self.protocol.upper()} statistic {xml_field}",
            )
            metric.add_metric([], self._number(statistics, xml_field))
            yield metric
