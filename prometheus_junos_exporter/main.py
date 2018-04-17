#!/usr/bin/env python3
import base64
import os
import socket
import threading
import time
import argparse
from prometheus_client import core, CONTENT_TYPE_LATEST, generate_latest, CollectorRegistry

from http.server import BaseHTTPRequestHandler, HTTPServer
from prometheus_junos_exporter.junos_exporter import JunosCollector
from prometheus_junos_exporter import __version__ as VERSION
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


def main():
    # Usage: junos_exporter.py port endpoint
    # Start up the server to expose the metrics.
    # Example Query
    # http://localhost:9332/metric?hostname=device.example.com&access=False&hostname=device2.example.com&access=True
    parser = argparse.ArgumentParser(
        prog='prometheus-junos-exporter',
        add_help=True,
        description='Simple metrics prometheus-junos-exporter for junos devices on your mettwork'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s {version}'.format(version=VERSION))
    parser.add_argument(
        '--ip',
        type=str,
        metavar='IP/FQDN',
        nargs='?',
        default='127.0.0.1',
        help='Address to bind port too.'
    )
    parser.add_argument(
        '--port',
        type=int,
        metavar='PORT',
        nargs='?',
        default=9332,
        help='PORT to listen on'
    )
    args = parser.parse_args()
    start_http_server(args.port, addr=args.ip)
    if not args.ip:
        args.ip = 'localhost'
    print("Using\thostname:\t{}\n\tport:\t\t{}".format(args.ip,args.port))
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()