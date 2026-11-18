from collections import Counter
from typing import Protocol, cast

import tornado
from prometheus_client import CollectorRegistry, Gauge, generate_latest

from .. import netstat


class MetricsApplication(Protocol):
    """What /metrics needs; served by the exporter and by the front door."""

    CONNECTIONS: Gauge
    multiprocess_registry: CollectorRegistry


class MetricsHandler(tornado.web.RequestHandler):
    """
    Tornado ``Handler`` that serves prometheus metrics.
    """

    @property
    def exporter(self) -> MetricsApplication:
        return cast(MetricsApplication, self.application)

    async def get_ssh_count(self):
        counts = Counter(tok["state"] for tok in [*netstat.ssh(v4=True), *netstat.ssh(v6=True)])
        for state, count in counts.items():
            self.exporter.CONNECTIONS.labels(state, "ssh").set(count)

    async def get_http_count(self):
        counts = Counter(tok["state"] for tok in [*netstat.http(v4=True), *netstat.http(v6=True)])
        for state, count in counts.items():
            self.exporter.CONNECTIONS.labels(state, "http").set(count)

    async def get_metrics(self):
        await self.get_ssh_count()
        await self.get_http_count()

    async def get(self):
        await self.get_metrics()
        self.set_header("Content-type", "text/plain")
        self.write(generate_latest(self.exporter.multiprocess_registry))
