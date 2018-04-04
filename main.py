
import base64
import os
import socket
import sys
import threading
import time
from prometheus_client import core, CONTENT_TYPE_LATEST, generate_latest, CollectorRegistry

from http.server import BaseHTTPRequestHandler, HTTPServer
from junos_exporter import JunosCollector
from socketserver import ThreadingMixIn
from urllib.request import build_opener, Request, HTTPHandler
from urllib.parse import quote_plus, parse_qs, urlparse

REQUESTER = set()


def start_http_server(port, addr='', registry=core.REGISTRY):
    """Starts an HTTP server for prometheus metrics as a daemon thread"""
    CustomMetricsHandler = MetricsHandler.factory(registry)
    httpd = _ThreadingSimpleServer((addr, port), CustomMetricsHandler)
    t = threading.Thread(target=httpd.serve_forever)
    t.daemon = True
    t.start()


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler that gives metrics from ``core.REGISTRY``."""
    registry = CollectorRegistry(auto_describe=False)

    def do_GET(self):
        global REQUESTER
        params = parse_qs(urlparse(self.path).query)
        host = None
        if 'hostname' in params and 'access' in params:
            if len(params['hostname']) == len(params['access']):
                try:
                    host = JunosCollector(params['hostname'], params['access'])
                    if not host in REQUESTER:
                        REQUESTER.add(host)
                        self.registry.register(host)
                    else:
                        host = None
                        pass
                except KeyError:
                    print("Key Error")
                    pass
        try:
            output = generate_latest(self.registry)
        except Exception as e:
            print(e)
            self.send_error(500, 'error generating metric output')
            raise
        self.send_response(200)
        self.send_header('Content-Type', CONTENT_TYPE_LATEST)
        self.end_headers()
        self.wfile.write(output)
        if host:
            try:
                REQUESTER.remove(host)
                self.registry.unregister(host)
            except KeyError:
                print("ignore")

    def log_message(self, format, *args):
        """Log nothing."""

    @staticmethod
    def factory(registry):
        """Returns a dynamic MetricsHandler class tied
           to the passed registry.
        """

        cls_name = str('MetricsHandler')
        MyMetricsHandler = type(cls_name, (MetricsHandler, object),
                                {"registry": registry})
        return MyMetricsHandler


class _ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    """Thread per request HTTP server."""


if __name__ == '__main__':
    # Usage: junos_exporter.py port endpoint
    # Start up the server to expose the metrics.
    # Example Query
    # http://localhost:8000/metric?hostname=device.example.com&access=False&hostname=device2.example.com&access=True
    point = 1
    ip = ''
    if len(sys.argv) > 2 and len(sys.argv) < 4:
        point = 2
        ip = sys.argv[1]
    elif len(sys.argv) >= 4:
        print("To many Arguments: {}\n max arg length = 2".format(len(sys.argv)))
        exit(1)
    try:
        port = int(sys.argv[point])
        print("Starting up Metrics endpoint")
    except ValueError:
        print("This is not a number: {}".format(sys.argv[point]))
        sys.exit(1)
    except IndexError:
        port=8000
    start_http_server(port, addr=ip)
    if not ip:
        ip = 'localhost'
    print("Using\thostname:\t{}\n\tport:\t\t{}".format(ip,port))
    while True:
        time.sleep(1)
