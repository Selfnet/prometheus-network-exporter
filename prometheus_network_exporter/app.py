import re
import os
import yaml
import getpass
import signal
import ipaddress
import argparse
import tornado.ioloop
import tornado.web
from fqdn import FQDN
from tornado import gen
from prometheus_client import Counter, Gauge, Info, REGISTRY, exposition, Summary
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from prometheus_network_exporter import __version__ as VERSION
from prometheus_network_exporter import Application
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
CONF_DIR = os.path.join('/etc', 'prometheus-network-exporter')

# Counter initialization
used_workers = Gauge('network_exporter_used_workers',
                     'The amount of workers being busy scraping Devices.')
total_workers = Gauge('network_exporter_workers',
                      'The total amount of workers')
total_workers.set(MAX_WORKERS)
SCRAPED_ERRORS = Counter('network_exporter_died_sessions',
                         'The count of exceptions raised by connection', ['hostname', 'exception'])
CONNECTIONS = Gauge('network_exporter_tcp_states',
                    'The count per tcp state and protocol', ['state', 'protocol'])


collectors = {
    'junos': JuniperMetrics(exception_counter=SCRAPED_ERRORS),
    'arubaos': ArubaMetrics(exception_counter=SCRAPED_ERRORS),
    'ios': CiscoMetrics(exception_counter=SCRAPED_ERRORS),
    'airmax': AirMaxMetrics(exception_counter=SCRAPED_ERRORS)
}


class MetricsHandler(tornado.web.RequestHandler):
    """
    Tornado ``Handler`` that serves prometheus metrics.
    """
    executor = ThreadPoolExecutor(max_workers=1)
    def initialize(self, registry=REGISTRY):
        self.registry = registry
    
    @run_on_executor
    def get_metrics(self):
        ssh = netstat.ssh(v4=True) + netstat.ssh(v6=True)
        http = netstat.http(v4=True) + netstat.http(v6=True)
        states = {}
        for conn in ssh:
            if not conn['state'] in states:
                states[conn['state']] = 0
            states[conn['state']] += 1
        for state, count in states.items():
            CONNECTIONS.labels(state, 'ssh').set(count)
        states = {}
        for conn in http:
            if not conn['state'] in states:
                states[conn['state']] = 0
            states[conn['state']] += 1
        for state, count in states.items():
            CONNECTIONS.labels(state, 'http').set(count)
        return

    @tornado.gen.coroutine
    def get(self):
        encoder, content_type = exposition.choose_encoder(
        self.request.headers.get('Accept'))
        self.set_header('Content-Type', content_type)
        yield self.get_metrics()
        self.write(encoder(self.registry))

class ExporterHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    @run_on_executor
    def get_device_information(self, hostname):
        # load config
        # start_time = datetime.now()
        # open device connection

        config = None
        with open(os.path.join(CONF_DIR, 'config.yml'), 'r') as f:
            config = yaml.load(f)
        if not Configuration().validate(config):
            print('{} :: Invalid Configuration for module {}'.format(
                hostname, module))
            return 500, 'Config Error', "Please fix your config."
        try:
            module = config[self.get_argument('module')]
        except tornado.web.MissingArgumentError:
            return 404, "you're holding it wrong!", "you're holding it wrong!:\n{}\n/metrics?module=default&target=target.example.com".format(
                self.request.uri)
        except KeyError:
            return 404, "Wrong module!", "you're holding it wrong!:\nAvailable modules are: {}".format(
                list(config.keys()))

        if not CONNECTION_POOL[hostname] or not CONNECTION_POOL[hostname].get('device'):
            CONNECTION_POOL[hostname] = {}
            dev = None
            if module['auth']['method'] == 'ssh_key':
                    # using ssh key
                if module['device'] == 'junos':
                    dev = JuniperNetworkDevice(hostname=hostname,
                                               user=module['auth'].get(
                                                   'username', getpass.getuser()),
                                               ssh_private_key_file=module['auth'].get(
                                                   'ssh_key', None),
                                               port=module['auth'].get(
                                                   'port', 22),
                                               ssh_config=module['auth'].get(
                                                   'ssh_config', None),
                                               password=module['auth'].get('password', None))
            elif module['auth']['method'] == 'password':
                try:
                    if module['device'] == 'arubaos':

                        http = 'https' if module['auth'].get(
                            'http_secure', True) else 'http'
                        port = module['auth'].get('port', 4343)
                        dev = ArubaNetworkDevice(
                            hostname=hostname,
                            username=module['auth'].get(
                                'username', getpass.getuser()),
                            password=module['auth']['password'],
                            protocol=http,
                            port=port,
                            proxy=module['auth'].get(
                                'proxy'),
                            verify=module['auth'].get(
                                'verify', False)
                        )
                    elif module['device'] == 'junos':
                        dev = JuniperNetworkDevice(
                            hostname=hostname,
                            user=module['auth'].get(
                                'username', getpass.getuser()),
                            password=module['auth']['password'],
                            port=module['auth'].get('port', 22)
                        )
                    elif module['device'] == 'airmax':
                        http = 'https' if module['auth'].get(
                            'http_secure', True) else 'http'
                        port = module['auth'].get('port', 443)
                        dev = AirMaxDevice(
                            hostname=hostname,
                            username=module['auth'].get(
                                'username', getpass.getuser()),
                            password=module['auth']['password'],
                            protocol=http,
                            port=port,
                            proxy=module['auth'].get(
                                'proxy'),
                            verify=module['auth'].get(
                                'verify', False)
                        )
                except KeyError:
                    return 500, 'Config Error', "You must specify a password."
            CONNECTION_POOL[hostname]['device'] = dev
        dev = CONNECTION_POOL[hostname]['device']
        # create metrics registry
        registry = Metrics()

        # get metrics from file
        types = module['metrics']

        return collectors[module['device']].metrics(types, dev, registry)

    @tornado.gen.coroutine
    def get(self):
        self.set_header('Content-type', 'text/plain')
        hostname = None
        try:
            hostname = self.get_argument('target')
        except tornado.web.MissingArgumentError:
            code, status, data = 404, "you're holding it wrong!", "you're holding it wrong!:\n{}\n/metrics?module=default&target=target.example.com".format(
                self.request.uri)
        except KeyError:
            code, status, data = 404, "Wrong module!", "you're holding it wrong!:\nAvailable modules are: {}".format(
                list(config.keys()))
        if not FQDN(hostname).is_valid:
            self.set_status(409, reason="FQDN is invalid!")
            self.write(bytes("{} is not a valid FQDN!".format(hostname)))
            return
        if hostname:
            if not hostname in CONNECTION_POOL.keys():
                CONNECTION_POOL[hostname] = {}

            used_workers.inc()
            CONNECTION_POOL[hostname]['locked'] = True
            code, status, data = yield self.get_device_information(hostname=hostname)
            CONNECTION_POOL[hostname]['locked'] = False
            used_workers.dec()

        self.set_status(code, reason=status)
        self.write(bytes(data, 'utf-8'))


class AllDeviceReloadHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(max_workers=1)

    @tornado.gen.coroutine
    def get(self):
        code, status = yield self.reload_all()

        self.set_status(code, reason=status)
        self.write(bytes(status, 'utf-8'))

    @run_on_executor
    def reload_all(self):
        entries = list(CONNECTION_POOL.keys())
        for entry in entries:
            if entry in CONNECTION_POOL and not CONNECTION_POOL[entry].get('locked', False):
                try:
                    CONNECTION_POOL[entry]['device'].disconnect()
                except (AttributeError, Exception, KeyError):
                    pass
                except:
                    pass
                del CONNECTION_POOL[entry]
                print("{} :: Connection Object {}".format(
                    entry, "deleted" if not entry in CONNECTION_POOL.keys() else "what the f***"))
        return 200, "Reloaded all!"


class DeviceReloadHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(max_workers=1)

    @run_on_executor
    def reload_device(self, hostname):
        if FQDN(hostname).is_valid:
            if hostname in CONNECTION_POOL and not CONNECTION_POOL[hostname].get('locked', False):
                try:
                    CONNECTION_POOL[hostname]['device'].disconnect()
                except (AttributeError, Exception, KeyError):
                    pass
                except:
                    pass
                del CONNECTION_POOL[hostname]
                print("{} :: Connection Object {}".format(
                    hostname, "deleted" if not hostname in CONNECTION_POOL.keys() else "what the f***"))
                return 200, 'Deleted!', "{} got deleted!".format(
                    hostname)
            else:
                return 404, 'Element not Found or Locked!', "{} is locked or not found.".format(
                    hostname)
        else:
            return 409, "FQDN is invalid!", "{} is not a valid FQDN!".format(
                hostname)

    @tornado.gen.coroutine
    def get(self, hostname):
        code, status, data = yield self.reload_device(hostname=hostname)
        self.set_status(code, reason=status)
        self.write(bytes(data, 'utf-8'))


class DisconnectHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(max_workers=1)

    @tornado.gen.coroutine
    def get(self, hostname):
        code, status, data = yield self.disconnect_all()
        self.set_status(code, reason=status)
        self.write(bytes(data, 'utf-8'))

    @run_on_executor
    def disconnect_all(self):
        for hostname, data in CONNECTION_POOL.items():
            try:
                data['device'].disconnect()
            except (AttributeError, Exception):
                pass
            except:
                pass
            print("{} :: Conection State {}".format(
                hostname, "Disconnected" if not data['device'].is_connected() else "Connected"))
        return 200, "OK", 'Shutdown Completed'


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
        (r'^/metrics$', MetricsHandler),
        (r'^/device$', ExporterHandler),
        (r'^/reload$', AllDeviceReloadHandler),
        (r'^/reload/(.*?)', DeviceReloadHandler)
    ]
    MAX_WORKERS = args.worker
    app = Application(urls)

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
            hostname, "Disconnected" if not data.get('device') or not data['device'].is_connected() else "Connected"))
    exit(0)


if __name__ == "__main__":
    app()
