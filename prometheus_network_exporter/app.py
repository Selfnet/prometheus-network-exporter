import argparse
import os
import signal
import sys
import time
import tracemalloc

import tornado.ioloop
import tornado.web

from prometheus_network_exporter import (
    APP_LOGGER,
    CONNECTION_POOL,
    COUNTER_DIR,
    GLOBAL_GUARD,
    MAX_WORKERS,
)
from prometheus_network_exporter import __version__ as VERSION
from prometheus_network_exporter.baseapp import Application
from prometheus_network_exporter.handlers.device import ExporterHandler
from prometheus_network_exporter.handlers.metrics import MetricsHandler
from prometheus_network_exporter.handlers.tracemalloc import TraceMallocHandler
from prometheus_network_exporter.handlers.unlock import DeviceUnlockHandler

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
    os.makedirs(COUNTER_DIR, mode=0o755, exist_ok=True)
    args = parser.parse_args()
    if args.debug:
        tracemalloc.start()
    urls = [
        (r"^/metrics$", MetricsHandler),
        (r"^/device$", ExporterHandler),
        (r"^/unlock/(.*?)", DeviceUnlockHandler),
        (r"^/memstats$", TraceMallocHandler),
    ]
    app = Application(
        urls,
        max_workers=args.worker,
        prometheus_buckets=[0.5, 1, 3, 5, 8, 13, 17, 21, 27, 34, 40, 55],
        debug=args.debug,
    )
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
    for hostname, data in CONNECTION_POOL.items():
        try:
            data.lock.acquire()
            data.disconnect()
        except Exception as e:
            APP_LOGGER.error(f"{hostname} :: Shutting down got {e}")
            APP_LOGGER.error(f"{hostname} :: {e.__traceback__}")
        finally:
            data.lock.release()
        APP_LOGGER.info(f"{hostname} :: Disconnected")
    SERVER.stop()
    GLOBAL_GUARD.release()
    sys.exit(0)


if __name__ == "__main__":
    app()
