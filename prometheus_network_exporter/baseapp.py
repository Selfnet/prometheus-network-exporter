import os
import yaml
from logging import getLogger
from prometheus_client import Histogram, Gauge, Counter, multiprocess, CollectorRegistry
from tornado.web import Application as _Application
from prometheus_network_exporter.schema import Configuration

log = getLogger("tornado_prometheus_exporter")
CONF_DIR = os.path.join("/etc", "prometheus-network-exporter")


class Application(_Application):
    """Adds Prometheus integration to Tornado"""

    def __init__(self, *args, **kwargs):
        """
        :param prometheus_registry: Prometheus registry that metrics are
            registered to.
        :param int prometheus_port: If not None, start prometheus server with
            given registry on given port.
        :param prometheus_buckets: Gets passed to prometheus_client.Histogram.
        """
        super(Application, self).__init__(*args, **kwargs)
        # self.registry = kwargs.pop('registry', REGISTRY)
        self.multiprocess_registry = CollectorRegistry(auto_describe=False)
        with open(os.path.join(CONF_DIR, "config.yml"), "r") as f:
            self.CONFIG = yaml.safe_load(f)
        Configuration().validate(self.CONFIG)
        multiprocess.MultiProcessCollector(
            registry=self.multiprocess_registry, path=".tmp"
        )
        self.max_workers = kwargs.pop("max_workers", 10)
        self.debug = kwargs.pop("debug", False)
        buckets = kwargs.pop("prometheus_buckets", None)
        histogram_kwargs = {
            "labelnames": ["method", "path", "status"],
            "registry": self.multiprocess_registry,
        }
        self.exception_counter = Counter(
            "network_exporter_raised_exceptions",
            "Count of raised Exceptions in the Exporter",
            ["exception", "collector", "hostname"],
            registry=self.multiprocess_registry,
        )
        # Counter initialization
        self.used_workers = Gauge(
            "network_exporter_used_workers",
            "The amount of workers being busy scraping Devices.",
            registry=self.multiprocess_registry,
        )
        self.total_workers = Gauge(
            "network_exporter_workers",
            "The total amount of workers",
            registry=self.multiprocess_registry,
        )
        self.total_workers.set(self.max_workers)

        self.CONNECTIONS = Gauge(
            "network_exporter_tcp_states",
            "The count per tcp state and protocol",
            ["state", "protocol"],
            registry=self.multiprocess_registry,
        )
        if buckets is not None:
            histogram_kwargs["buckets"] = buckets
        self.request_time_histogram = Histogram(
            "tornado_http_request_duration_seconds",
            "Tornado HTTP request duration in seconds",
            **histogram_kwargs
        )

    def log_request(self, handler):
        """Adds request metrics to the Prometheus export"""
        super(Application, self).log_request(handler)
        self.request_time_histogram.labels(
            method=handler.request.method.lower(),
            path=handler.request.uri.lower(),
            status=int(handler.get_status()),
        ).observe(handler.request.request_time())
