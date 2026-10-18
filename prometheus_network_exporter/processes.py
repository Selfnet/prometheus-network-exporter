"""Several worker processes behind one HTTP port.

A Python process runs its collectors on one CPU core, however many threads
it has. With ``--processes N`` the main process forks N workers, each a
complete exporter on a loopback port, and forwards every ``/device`` and
``/unlock`` request to the worker that owns the target. The owner is the
hash of the hostname, so a switch always lands in the same process and its
connection pool, session slot and kept NETCONF session stay in one place.

``/metrics`` is served by the main process from the multiprocess directory
of prometheus_client, into which every process writes its own counters.
When a worker dies the main process exits; systemd restarts the whole set.
"""

from __future__ import annotations

import glob
import multiprocessing
import os
import signal
import sys
import zlib
from typing import Callable, List

import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.iostream
import tornado.netutil
import tornado.simple_httpclient
import tornado.web
from prometheus_client import CollectorRegistry, Gauge, multiprocess

from prometheus_network_exporter import APP_LOGGER, COUNTER_DIR, MAX_WAIT_SECONDS_BEFORE_SHUTDOWN
from prometheus_network_exporter.handlers.metrics import MetricsHandler
from prometheus_network_exporter.handlers.tracemalloc import TraceMallocHandler

# Prometheus controls the scrape timeout; the proxy must not cut a long
# route table dump short before Prometheus gives up on it.
FORWARD_TIMEOUT_SECONDS = 600
WORKER_START_TIMEOUT_SECONDS = 60
# Errors of the hop to the worker, as opposed to an HTTP status the worker
# itself answered with; those are passed through unchanged.
TRANSPORT_ERRORS = (
    OSError,
    tornado.iostream.StreamClosedError,
    tornado.simple_httpclient.HTTPTimeoutError,
    tornado.simple_httpclient.HTTPStreamClosedError,
)


def shard_for(hostname: str, processes: int) -> int:
    """Index of the worker that owns the target; stable across restarts."""
    return zlib.crc32(hostname.encode("utf-8")) % processes


def clear_counter_dir(path: str = COUNTER_DIR) -> None:
    """Drop the counter files of a previous run before the workers start."""
    for file in glob.glob(os.path.join(path, "*.db")):
        try:
            os.remove(file)
        except OSError:
            pass


class ProxyHandler(tornado.web.RequestHandler):
    """Forwards one request to the worker that owns its target."""

    async def get(self, hostname: str = None):
        target = hostname if hostname is not None else self.get_argument("target", "")
        port = self.application.port_for(target)
        url = f"http://127.0.0.1:{port}{self.request.uri}"
        try:
            # raise_error=False keeps HTTP statuses of the worker; errors of
            # the hop itself (refused, closed, timed out) are still raised.
            response = await self.application.client.fetch(
                url, raise_error=False, connect_timeout=5, request_timeout=FORWARD_TIMEOUT_SECONDS
            )
        except TRANSPORT_ERRORS as error:
            response = None
            reason = error
        else:
            reason = response.error if response.code == 599 else None
        if response is None or reason is not None:
            APP_LOGGER.error("%s :: worker on port %s did not answer: %s", target, port, reason)
            self.set_status(502, reason="worker unreachable")
            self.write(f"{target}: worker process did not answer".encode("utf-8"))
            return
        self.set_status(response.code, reason=response.reason)
        content_type = response.headers.get("Content-Type")
        if content_type:
            self.set_header("Content-Type", content_type)
        self.write(response.body or b"")


class ProxyApplication(tornado.web.Application):
    """The front door: forwards scrapes, serves the aggregated /metrics."""

    def __init__(self, ports: List[int], max_clients: int = 200, debug: bool = False):
        urls = [
            (r"^/metrics$", MetricsHandler),
            (r"^/device$", ProxyHandler),
            (r"^/unlock/(.*?)$", ProxyHandler),
            (r"^/memstats$", TraceMallocHandler),
        ]
        super().__init__(urls, debug=debug)
        self.ports = list(ports)
        tornado.httpclient.AsyncHTTPClient.configure(None, max_clients=max_clients)
        self.client = tornado.httpclient.AsyncHTTPClient()
        # Only the collector: in multiprocess mode the metric objects of every
        # process write files, registering them here as well would list them twice.
        os.makedirs(COUNTER_DIR, mode=0o755, exist_ok=True)
        self.multiprocess_registry = CollectorRegistry(auto_describe=False)
        multiprocess.MultiProcessCollector(registry=self.multiprocess_registry, path=COUNTER_DIR)
        self.CONNECTIONS = Gauge(
            "network_exporter_tcp_states",
            "The count per tcp state and protocol",
            ["state", "protocol"],
            multiprocess_mode="livesum",
            registry=None,
        )

    def port_for(self, hostname: str) -> int:
        return self.ports[shard_for(hostname, len(self.ports))]


def run_worker(index: int, build_application: Callable, conn) -> None:
    """Body of one worker process: the whole exporter on a loopback port."""
    sockets = tornado.netutil.bind_sockets(0, "127.0.0.1")
    port = sockets[0].getsockname()[1]
    application = build_application()
    server = tornado.httpserver.HTTPServer(application)
    server.add_sockets(sockets)
    APP_LOGGER.info("worker %d (pid %d) listening on 127.0.0.1:%d", index, os.getpid(), port)
    conn.send(port)
    conn.close()
    # The main process ends the workers; they only clean up their sessions.
    from prometheus_network_exporter import app as app_module

    app_module.SERVER = server
    signal.signal(signal.SIGTERM, app_module.sig_handler)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    tornado.ioloop.IOLoop.current().start()


def start_workers(processes: int, build_application: Callable) -> tuple:
    """Fork the workers and wait until every one reports its port."""
    context = multiprocessing.get_context("fork")
    workers, ports = [], []
    for index in range(processes):
        parent, child = context.Pipe(duplex=False)
        process = context.Process(
            target=run_worker, args=(index, build_application, child), name=f"worker-{index}", daemon=False
        )
        process.start()
        child.close()
        workers.append(process)
        if not parent.poll(WORKER_START_TIMEOUT_SECONDS):
            raise RuntimeError(f"worker {index} did not report its port")
        ports.append(parent.recv())
        parent.close()
    return workers, ports


def serve(args, build_application: Callable) -> None:
    """Main process: workers first, then the front door on the public port."""
    clear_counter_dir()
    workers, ports = start_workers(args.processes, build_application)
    application = ProxyApplication(ports, max_clients=max(args.worker, 100), debug=args.debug)
    server = tornado.httpserver.HTTPServer(application)
    loop = tornado.ioloop.IOLoop.current()

    def stop(sig, frame):
        APP_LOGGER.info("Caught signal: %s, stopping %d workers", sig, len(workers))
        loop.add_callback_from_signal(shutdown)

    def shutdown():
        server.stop()
        for worker in workers:
            if worker.is_alive():
                os.kill(worker.pid, signal.SIGTERM)
        for worker in workers:
            worker.join(MAX_WAIT_SECONDS_BEFORE_SHUTDOWN)
        loop.stop()

    def watch():
        dead = [w for w in workers if not w.is_alive()]
        if dead:
            APP_LOGGER.error("worker %s died, exiting so that systemd restarts the exporter", [w.name for w in dead])
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
            sys.exit(1)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    tornado.ioloop.PeriodicCallback(watch, 5000).start()
    APP_LOGGER.info(
        "Starting HTTP Server on http://%s:%s with %d worker processes", args.ip, args.port, len(workers)
    )
    server.listen(args.port, address=args.ip)
    loop.start()
    APP_LOGGER.info("Exiting ...")
