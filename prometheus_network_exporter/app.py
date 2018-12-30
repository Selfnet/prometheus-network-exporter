import re
import os
import yaml
import getpass
import signal
import ipaddress
import argparse
import tornado.ioloop
import tornado.web
from tornado import gen
from prometheus_client import Counter, Gauge, Info, REGISTRY, exposition
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from prometheus_network_exporter import __version__ as VERSION
from prometheus_network_exporter.registry import Metrics
from prometheus_network_exporter.devices.junosdevice import JuniperNetworkDevice, JuniperMetrics
from prometheus_network_exporter.devices.arubadevice import ArubaNetworkDevice, ArubaMetrics
from prometheus_network_exporter.devices.ubntdevice import AirMaxDevice, AirMaxMetrics
from prometheus_network_exporter.devices.ciscodevice import CiscoNetworkDevice, CiscoMetrics
from prometheus_network_exporter.schema import Configuration
import prometheus_network_exporter.netstat as netstat
CONNECTION_POOL = {}
MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 30
MAX_WORKERS = 150
config = None
SERVER = None

## Counter initialization
used_workers = Gauge('network_exporter_used_workers', 'The amount of workers being busy scraping Devices.')
total_workers = Gauge('network_exporter_workers', 'The total amount of workers')
total_workers.set(MAX_WORKERS)
scraped_errors = Counter('network_exporter_died_sessions', 'The count of exceptions raised by connection', ['hostname', 'exception'])
connections = Gauge('network_exporter_tcp_states', 'The count per tcp state and protocol', ['state', 'protocol'])
collectors = {
    'junos': JuniperMetrics(exception_counter=scraped_errors),
    'arubaos': ArubaMetrics(exception_counter=scraped_errors),
    'ios': CiscoMetrics(exception_counter=scraped_errors),
    'airmax': AirMaxMetrics(exception_counter=scraped_errors)
}

class MetricsHandler(tornado.web.RequestHandler):
    """
    Tornado ``Handler`` that serves prometheus metrics.
    """
    def initialize(self, registry=REGISTRY):
        self.registry = registry

    def get(self):
        encoder, content_type = exposition.choose_encoder(self.request.headers.get('Accept'))
        ssh = netstat.ssh(v4=True) + netstat.ssh(v6=True)
        http = netstat.http(v4=True) + netstat.http(v6=True)
        states = {}
        for conn in ssh:
            if not conn['state'] in states:
                states[conn['state']] = 0
            states[conn['state']] += 1
        for state, count in states.items():
            connections.labels(state, 'ssh').set(count)
        states = {}
        for conn in http:
            if not conn['state'] in states:
                states[conn['state']] = 0
            states[conn['state']] += 1
        for state, count in states.items():
            connections.labels(state, 'http').set(count)
        self.set_header('Content-Type', content_type)
        self.write(encoder(self.registry))

class ExporterHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    @run_on_executor
    def get_device_information(self):
        # load config
        # start_time = datetime.now()
        CONF_DIR = os.path.join('/etc', 'prometheus-network-exporter')
        with open(os.path.join(CONF_DIR, 'config.yml'), 'r') as f:
            config = yaml.load(f)
        if not Configuration().validate(config):
            print('Invalid Configuration!')
            exit(1)
        # parameters from url
        # get profile from config
        try:
            profile = config[self.get_argument('module')]
            hostname = self.get_argument('target')
        except tornado.web.MissingArgumentError:
            return 404, "you're holding it wrong!", "you're holding it wrong!:\n{}\n/metrics?module=default&target=target.example.com".format(self.request.uri)
        except KeyError:
            return 404, "Wrong module!", "you're holding it wrong!:\nAvailable modules are: {}".format(list(config.keys()))
        # open device connection
        if not hostname in CONNECTION_POOL.keys() or not CONNECTION_POOL[hostname] or not CONNECTION_POOL[hostname]['device']:
            dev = None
            if profile['auth']['method'] == 'ssh_key':
                    # using ssh key
                if profile['device'] == 'junos':
                    dev = JuniperNetworkDevice(hostname=hostname,
                                               user=profile['auth'].get(
                                                   'username', getpass.getuser()),
                                               ssh_private_key_file=profile['auth'].get(
                                                   'ssh_key', None),
                                               port=profile['auth'].get(
                                                   'port', 22),
                                               ssh_config=profile['auth'].get(
                                                   'ssh_config', None),
                                               password=profile['auth'].get('password', None))
            elif profile['auth']['method'] == 'password':
                try:
                    if profile['device'] == 'arubaos':

                        http = 'https' if profile['auth'].get(
                            'http_secure', True) else 'http'
                        port = profile['auth'].get('port', 4343)
                        dev = ArubaNetworkDevice(
                            hostname=hostname,
                            username=profile['auth'].get(
                                'username', getpass.getuser()),
                            password=profile['auth']['password'],
                            protocol=http,
                            port=port,
                            proxy=profile['auth'].get(
                                'proxy'),
                            verify=profile['auth'].get(
                                'verify', False)
                        )
                    elif profile['device'] == 'junos':
                        dev = JuniperNetworkDevice(
                            hostname=hostname,
                            user=profile['auth'].get(
                                'username', getpass.getuser()),
                            password=profile['auth']['password'],
                            port=profile['auth'].get('port', 22)
                        )
                    elif profile['device'] == 'airmax':
                        http = 'https' if profile['auth'].get(
                            'http_secure', True) else 'http'
                        port = profile['auth'].get('port', 443)
                        dev = AirMaxDevice(
                            hostname=hostname,
                            username=profile['auth'].get(
                                'username', getpass.getuser()),
                            password=profile['auth']['password'],
                            protocol=http,
                            port=port,
                            proxy=profile['auth'].get(
                                'proxy'),
                            verify=profile['auth'].get(
                                'verify', False)
                        )
                except KeyError:
                    return 500, 'Config Error', "You must specify a password."
            CONNECTION_POOL[hostname] = {}
            CONNECTION_POOL[hostname]['device'] = dev
        dev = CONNECTION_POOL[hostname]['device']
        # create metrics registry
        registry = Metrics()

        # get metrics from file
        types = profile['metrics']

        return collectors[profile['device']].metrics(types, dev, registry)

    @tornado.gen.coroutine
    def get(self):
        self.set_header('Content-type', 'text/plain')
        used_workers.inc()
        code, status, data = yield self.get_device_information()
        used_workers.dec()
        self.set_status(code, reason=status)
        self.write(bytes(data, 'utf-8'))


class DisconnectHandler(tornado.web.RequestHandler):
    def get(self):
        for hostname, data in CONNECTION_POOL.items():
            try:
                data['device'].disconnect()
            except (AttributeError, Exception):
                pass
            except:
                pass
            print("{} :: Conection State {}".format(
                hostname, "Disconnected" if not device.is_connected() else "Connected"))
        self.set_status(200, reason="OK")
        self.set_header('Content-type', 'text/plain')
        self.write(bytes('Shutdown Completed', 'utf-8'))


def app():
    global MAX_WORKERS
    parser = argparse.ArgumentParser(prog='prometheus-network-exporter',
                                     description="Prometheus exporter for JunOS switches and routers + Others")
    parser.add_argument('--version', action='version',
                        version='%(prog)s{}'.format(VERSION))
    parser.add_argument('--port', type=int, default=9332,
                        help="Specifys the port on which the exporter is running.(Default=9332)")
    parser.add_argument('--ip', type=str, default="::1",
                        help="Specifys the port on which the exporter is running.(Default=::1)")
    parser.add_argument('--worker', type=int, default=150,
                        help="Specifys the max concurrent threads running for the metrics collection. (Default=150)")

    args = parser.parse_args()
    urls = [
        (r'^/disconnect$', DisconnectHandler),
        (r'^/disconnect/$', DisconnectHandler),
        (r'^/metrics$', MetricsHandler),
        (r'^/device$', ExporterHandler)
    ]
    MAX_WORKERS = args.worker
    app = tornado.web.Application(urls)

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    global SERVER
    SERVER = tornado.httpserver.HTTPServer(app)
    print("Listening on http://{}:{}".format(args.ip, args.port))
    SERVER.listen(args.port, address=args.ip)

    tornado.ioloop.IOLoop.current().start()
    print("Exiting ...")


def sig_handler(sig, frame):
    print('Caught signal: {}'.format(sig))
    tornado.ioloop.IOLoop.current().add_callback(shutdown)


def shutdown():
    print('Stopping http server')
    SERVER.stop()
    for hostname, data in CONNECTION_POOL.items():
        try:
            data['device'].disconnect()
        except (AttributeError, Exception):
            pass
        except:
            pass
        print("{} :: Connection State {}".format(
            hostname, "Disconnected" if not data['device'].is_connected() else "Connected"))
    exit(0)


if __name__ == "__main__":
    app()
