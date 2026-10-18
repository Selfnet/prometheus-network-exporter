"""Scrape health: failed RPCs, RPC durations and unexpected XML schemas."""

from __future__ import annotations

from prometheus_client.core import GaugeMetricFamily

from ..base import Collector
from . import base


class StatusCollector(Collector):
    """Registered last so that it sees what every other collector recorded."""

    def __init__(self, device):
        super().__init__(base, device, config={})

    def collect(self):
        failed = GaugeMetricFamily(
            f"{base}_rpc_failed",
            "1 when the RPC raised an error during this scrape",
            labels=["rpc"],
        )
        for name in sorted(self.device.rpc_failed):
            failed.add_metric([name], 1.0)
        yield failed

        duration = GaugeMetricFamily(
            f"{base}_rpc_duration_seconds",
            "Wall clock time of each RPC during this scrape",
            labels=["rpc"],
        )
        for name, value in sorted(self.device.rpc_durations.items()):
            duration.add_metric([name], value)
        yield duration

        connect = GaugeMetricFamily(
            f"{base}_netconf_connect_seconds",
            "Time to open the NETCONF session for this scrape; slow when the "
            "routing engine is busy",
        )
        if self.device.connect_duration is not None:
            connect.add_metric([], self.device.connect_duration)
        yield connect

        aborted = GaugeMetricFamily(
            f"{base}_scrape_aborted",
            "1 when the device stopped answering during this scrape; only the "
            "status metrics are reported then, rpc_failed names the RPC that hung",
            labels=["reason"],
        )
        reason = getattr(self.device, "aborted", None)
        aborted.add_metric([reason or ""], 1.0 if reason else 0.0)
        yield aborted

        reused = GaugeMetricFamily(
            f"{base}_netconf_session_reused",
            "1 when this scrape reused the NETCONF session of the previous one "
            "(keep_session); netconf_connect_seconds is then absent",
        )
        reused.add_metric([], 1.0 if getattr(self.device, "session_reused", False) else 0.0)
        yield reused

        collector_duration = GaugeMetricFamily(
            f"{base}_collector_duration_seconds",
            "Wall clock time of each collector during this scrape, including its RPCs",
            labels=["collector"],
        )
        for name, value in sorted(self.device.collector_durations.items()):
            collector_duration.add_metric([name], value)
        yield collector_duration

        collector_failed = GaugeMetricFamily(
            f"{base}_collector_failed",
            "1 when the collector raised an error during this scrape; its "
            "metrics are incomplete, the other collectors are not affected",
            labels=["collector"],
        )
        for name in sorted(self.device.collector_failed):
            collector_failed.add_metric([name], 1.0)
        yield collector_failed

        missing = GaugeMetricFamily(
            f"{base}_xml_missing_fields",
            "Expected XML fields that were absent from the RPC reply during "
            "this scrape; non-zero means the Junos release differs from what "
            "the collector expects",
            labels=["collector", "field"],
        )
        for (collector, field), count in sorted(self.device.schema.missing.items()):
            missing.add_metric([collector, field], float(count))
        yield missing
