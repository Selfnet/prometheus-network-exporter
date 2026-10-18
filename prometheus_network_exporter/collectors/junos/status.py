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
