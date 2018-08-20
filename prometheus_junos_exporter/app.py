import re
import os
import yaml
import getpass
import signal
from datetime import datetime
import argparse
import tornado.ioloop
import tornado.web
from tornado import gen
from prometheus_junos_exporter import __version__ as VERSION
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from prometheus_junos_exporter import wrapping
from prometheus_junos_exporter.devices.junosdevice import JuniperNetworkDevice
CONNECTION_POOL = {}
MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 30
MAX_WORKERS = 150
wrapping.init()
config = None
SERVER = None

class Metrics(object):
    """
    Store metrics and do conversions to PromQL syntax
    """

    class _Metric(object):
        """
        This is an actual metric entity
        """

        def __init__(self, name, value, metric_type, labels=None):
            self.name = name
            self.value = float(value)
            self.metric_type = metric_type
            self.labels = []
            if labels:
                for label_name, label_value in labels.items():
                    self.labels.append(
                        '{}="{}"'.format(label_name, label_value))

        def __str__(self):
            return "{}{} {}".format(self.name, "{" + ",".join(self.labels) + "}", self.value)

    def __init__(self):
        self._metrics_registry = {}
        self._metric_types = {}
        self._metrics_description = {}

    def register(self, name, description, metric_type):
        """
        Add a metric to the registry
        """
        if self._metrics_registry.get(name) is None:
            self._metrics_registry[name] = []
            self._metric_types[name] = metric_type
            self._metrics_description[name] = description
        else:
            raise ValueError(
                'Metric named {} is already registered.'.format(name))

    def add_metric(self, name, value, labels=None):
        """
        Add a new metric
        """
        collector = self._metrics_registry.get(name)
        if collector is None:
            raise ValueError('Metric named {} is not registered.'.format(name))

        metric = self._Metric(name, value, self._metric_types[name], labels)
        collector.append(metric)

    def collect(self):
        """
        Collect all metrics and return
        """
        lines = []
        for name, metric_type in self._metric_types.items():
            lines.append("# HELP {} {}".format(
                name, self._metrics_description[name]))
            lines.append("# TYPE {} {}".format(name, metric_type))
            lines.extend(self._metrics_registry[name])
        return "\n".join([str(x) for x in lines]) + '\n'


def get_interface_metrics(registry, dev, hostname, access=True, ospf=True, optics=True):
    """
    Get interface metrics
    """
    # interfaces
    interfaces = {}
    if access:
        interfaces = dev.get_interface(
            interface_names=wrapping.NETWORK_REGEXES, optics=optics, ospf=ospf)
    else:
        interfaces = dev.get_interface(optics=optics, ospf=ospf)
    if ospf:
        for MetricName, MetricFamily in wrapping.METRICS.items():
            for metrik_def in wrapping.OSPF_METRICS.get(MetricName, []):
                name, description, key, function, _ = wrapping.create_metrik_params(
                    metrik_def)
                for ospf in ['ospf', 'ospf3']:
                    metrik_name = "{}_{}_{}_{}".format(wrapping.METRICS_BASE.get(
                        'base', 'junos'),
                        wrapping.METRICS_BASE.get('interface', 'interface'),
                        ospf,
                        name)
                    registry.register(metrik_name, description, MetricFamily)
                    for interface, metriken in interfaces.items():
                        for unit, data in metriken.get(ospf, {}).items():
                            if data.get(key) is not None:
                                labels_data = {'hostname': hostname,
                                               'interface': interface,
                                               'unit': unit}
                                labels_variable = {label['label']: metriken.get(
                                    label['key'], "") for label in wrapping.NETWORK_LABEL_WRAPPER}
                                labels_ospf = {label['label']: data.get(
                                    label['key'], "") for label in wrapping.OSPF_LABEL_WRAPPER}
                                labels = {**labels_data, **
                                          labels_variable, **labels_ospf}
                                wrapping.create_metrik(metrik_name,
                                                       registry, key, labels, data, function=function)

    for MetricName, MetricFamily in wrapping.METRICS.items():
        for metrik_def in wrapping.NETWORK_METRICS.get(MetricName, []):
            metrik_name, description, key, function, _ = wrapping.create_metrik_params(
                metrik_def)
            metrik_name = "{}_{}_{}".format(wrapping.METRICS_BASE.get(
                'base', 'junos'), wrapping.METRICS_BASE.get('interface', 'interface'), metrik_name)
            registry.register(metrik_name, description, MetricFamily)
            for interface, metriken in interfaces.items():
                if metriken.get(key) is not None:
                    labels_data = {'hostname': hostname,
                                   'interface': interface}
                    labels_variable = {label['label']: metriken.get(
                        label['key'], "") for label in wrapping.NETWORK_LABEL_WRAPPER}
                    labels = {**labels_data, **labels_variable}
                    wrapping.create_metrik(metrik_name,
                                           registry, key, labels, metriken, function=function)


def get_environment_metrics(registry, dev, hostname):
    """
    Get environment metrics
    """
    environment = dev.get_environment()
    for MetricName, MetricFamily in wrapping.METRICS.items():
        for metrik_def in wrapping.ENVIRONMENT_METRICS.get(MetricName, []):
            metrik_name, description, key, function, specific = wrapping.create_metrik_params(
                metrik_def)
            metrik_name = "{}_{}_{}".format(
                wrapping.METRICS_BASE['base'], wrapping.METRICS_BASE['device'], metrik_name)
            registry.register(metrik_name, description, MetricFamily)
            labels_data = {'hostname': hostname}
            labels_variable = {label['label']: environment.get(
                label['key'], "") for label in wrapping.ENVIRONMENT_LABEL_WRAPPER}
            labels = {**labels_data, **labels_variable}
            if specific and function:
                data = environment.get(key, None)
                wrapping.FUNCTIONS[function](
                    metrik_name, registry, labels, data, create_metrik=wrapping.create_metrik)
            elif environment.get(key):
                wrapping.create_metrik(
                    metrik_name, registry, key, labels, environment, function=function)


def get_bgp_metrics(registry, dev, hostname):
    """
    Get BGP neighbor metrics
    """
    bgp = dev.get_bgp()
    for MetricName, MetricFamily in wrapping.METRICS.items():
        for metrik_def in wrapping.BGP_METRICS.get(MetricName, []):
            metrik_name, description, key, function, _ = wrapping.create_metrik_params(
                metrik_def)
            metrik_name = "{}_{}_{}".format(
                wrapping.METRICS_BASE['base'], wrapping.METRICS_BASE['bgp'], metrik_name)
            registry.register(metrik_name, description, MetricFamily)
            if bgp:
                for peername, metriken in bgp.items():
                    if metriken.get(key) is not None:
                        labels_data = {'hostname': hostname,
                                       'peername': peername}
                        labels_variable = {label['key']: metriken.get(
                            label['key'], "") for label in wrapping.BGP_LABEL_WRAPPER}
                        labels = {**labels_data, **labels_variable}
                        wrapping.create_metrik(
                            metrik_name, registry, key, labels, metriken, function=function)


class MetricsHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    @run_on_executor
    def get_device_information(self):
        # load config
        start_time = datetime.now()
        CONF_DIR = os.path.join('/etc', 'prometheus-junos-exporter')
        with open(os.path.join(CONF_DIR, 'config.yml'), 'r') as f:
            config = yaml.load(f)
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
        if not hostname in CONNECTION_POOL.keys() or not CONNECTION_POOL[hostname]:
            if profile['auth']['method'] == 'password':
                # using regular username/password
                dev = JuniperNetworkDevice(host=hostname,
                                           user=profile['auth'].get(
                                               'username', getpass.getuser()),
                                           password=profile['auth'].get(
                                               'password', None),
                                           port=profile['auth'].get('port', 22))
            elif profile['auth']['method'] == 'ssh_key':
                # using ssh key
                dev = JuniperNetworkDevice(host=hostname,
                                           user=profile['auth'].get(
                                               'username', getpass.getuser()),
                                           ssh_private_key_file=profile['auth'].get(
                                               'ssh_key', None),
                                           port=profile['auth'].get(
                                               'port', 22),
                                           ssh_config=profile['auth'].get(
                                               'ssh_config', None),
                                           password=profile['auth'].get('password', None))
            CONNECTION_POOL[hostname] = dev
        dev = CONNECTION_POOL[hostname]
        connected = dev.reconnect()
        # create metrics registry
        registry = Metrics()

        # get and parse metrics
        types = profile['metrics']
        optics = ospf = True
        if connected:
            try:
                if not 'ospf' in types:
                    ospf = False
                if not 'optics' in types:
                    optics = False
                if 'interface' in types:
                    get_interface_metrics(registry, dev, hostname,
                                        access=False, optics=optics, ospf=ospf)
                if 'interface_specifics' in types:
                    get_interface_metrics(registry, dev, hostname,
                                        access=True, optics=optics, ospf=ospf)
                if 'environment' in types:
                    get_environment_metrics(registry, dev, hostname)
                if 'bgp' in types:
                    get_bgp_metrics(registry, dev, hostname)
            except AttributeError as e:
                print(e)
                return 500, "Device unreachable", "Device {} unreachable".format(hostname)
            print("{} :: {} :: took :: {} :: to be completed".format(
                hostname, start_time, datetime.now() - start_time))
            return 200, "OK", registry.collect()
        return 500, "Device unreachable", "Device {} unreachable".format(hostname)

    @tornado.   gen.coroutine
    def get(self):
        self.set_header('Content-type', 'text/plain')
        code, status, data = yield self.get_device_information()
        self.set_status(code, reason=status)
        self.write(bytes(data, 'utf-8'))


class DisconnectHandler(tornado.web.RequestHandler):
    def get(self):
        for hostname, device in CONNECTION_POOL.items():
            device.disconnect()
            print("{} :: Conection State {}".format(
                hostname, "Disconnected" if not device.is_connected() else "Connected"))
        self.set_status(200, reason="OK")
        self.set_header('Content-type', 'text/plain')
        self.write(bytes('Shutdown Completed', 'utf-8'))


def app():
    global MAX_WORKERS
    parser = argparse.ArgumentParser(prog='prometheus-junos-exporter',
                                     description="Prometheus exporter for JunOS switches and routers.")
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
        (r'^/metrics/?$', MetricsHandler),
        (r'^/metrics/(.+)$', MetricsHandler)
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
    for hostname, device in CONNECTION_POOL.items():
        device.disconnect()
        print("{} :: Conection State {}".format(
            hostname, "Disconnected" if not device.is_connected() else "Connected"))
    exit(0)


if __name__ == "__main__":
    app()
