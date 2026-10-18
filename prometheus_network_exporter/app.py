import argparse
import os
import signal
import sys
import time
import tracemalloc

# Every process writes its own counters into this directory and the main
# process aggregates them for /metrics. prometheus_client decides on this at
# its first import, so it has to be set before anything imports it.
os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", ".tmp")

import tornado.httpserver  # noqa: E402
import tornado.ioloop  # noqa: E402
import tornado.web  # noqa: E402

from prometheus_network_exporter import (  # noqa: E402
    APP_LOGGER,
    CONNECTION_POOL,
    COUNTER_DIR,
    GLOBAL_GUARD,
    MAX_WORKERS,
)
from prometheus_network_exporter import __version__ as VERSION  # noqa: E402
from prometheus_network_exporter import processes  # noqa: E402
from prometheus_network_exporter.baseapp import Application  # noqa: E402
from prometheus_network_exporter.handlers.device import ExporterHandler  # noqa: E402
from prometheus_network_exporter.handlers.metrics import MetricsHandler  # noqa: E402
from prometheus_network_exporter.handlers.tracemalloc import TraceMallocHandler  # noqa: E402
from prometheus_network_exporter.handlers.unlock import DeviceUnlockHandler  # noqa: E402

if not sys.warnoptions:
    import warnings

    warnings.simplefilter("ignore")

SERVER = None


def app():
    global APP_LOGGER, MAX_WORKERS, SERVER, COUNTER_DIR
    parser = argparse.ArgumentParser(
        prog="prometheus-network-exporter",
        description="Prometheus exporter for JunOS switches and routers + Others",
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s: {}".format(VERSION)
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9332,
        help="Specifys the port on which the exporter is running.(Default=9332)",
    )
    parser.add_argument(
        "--ip",
        type=str,
        default="::1",
        help="Specifys the port on which the exporter is running.(Default=::1)",
    )
    parser.add_argument(
        "--worker",
        type=int,
        default=10,
        help="Specifys the max concurrent threads running for the metrics collection. (Default=150)",
    )
    parser.add_argument(
        "--debug",
        type=bool,
        default=False,
        help="Enables the Debug Tracemalloc interface.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path of the config file. (Default=/etc/prometheus-network-exporter/config.yml)",
    )
    parser.add_argument(
        "--processes",
        type=int,
        default=1,
        help="Worker processes behind the port; a target always lands in the same one. "
        "A process scrapes on one CPU core, so use one per core the exporter may have. (Default=1)",
    )
    os.makedirs(COUNTER_DIR, mode=0o755, exist_ok=True)
    args = parser.parse_args()
    if args.debug:
        tracemalloc.start()

    def build_application():
        urls = [
            (r"^/metrics$", MetricsHandler),
            (r"^/device$", ExporterHandler),
            (r"^/unlock/(.*?)", DeviceUnlockHandler),
            (r"^/memstats$", TraceMallocHandler),
        ]
        return Application(
            urls,
            max_workers=args.worker,
            prometheus_buckets=[0.5, 1, 3, 5, 8, 13, 17, 21, 27, 34, 40, 55],
            debug=args.debug,
            config_path=args.config,
        )

    if args.processes > 1:
        processes.serve(args, build_application)
        return

    processes.clear_counter_dir()
    app = build_application()
    MAX_WORKERS = app.max_workers
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)
    SERVER = tornado.httpserver.HTTPServer(app)
    APP_LOGGER.info("Starting HTTP Server on http://{}:{}".format(args.ip, args.port))
    SERVER.listen(args.port, address=args.ip)

    tornado.ioloop.IOLoop.current().start()
    APP_LOGGER.info("Exiting ...")


def sig_handler(sig, frame):
    global APP_LOGGER
    APP_LOGGER.info("Caught signal: {}".format(sig))
    tornado.ioloop.IOLoop.current().add_callback_from_signal(shutdown)


def shutdown():
    global SERVER, GLOBAL_GUARD, APP_LOGGER
    GLOBAL_GUARD.acquire(True)
    APP_LOGGER.info("Sleeping for 60s")
    time.sleep(5)
    APP_LOGGER.warning("Stopping http server")
    for key, data in list(CONNECTION_POOL.items()):
        if data is None:
            continue
        if not data.lock.acquire(timeout=5):
            APP_LOGGER.error(f"{key} :: still scraping, not disconnected")
            continue
        try:
            data.disconnect()
        except Exception as e:
            APP_LOGGER.error(f"{key} :: Shutting down got {e}")
            APP_LOGGER.error(f"{key} :: {e.__traceback__}")
        finally:
            data.lock.release()
        APP_LOGGER.info(f"{key} :: Disconnected")
    SERVER.stop()
    GLOBAL_GUARD.release()
    sys.exit(0)


if __name__ == "__main__":
    app()
