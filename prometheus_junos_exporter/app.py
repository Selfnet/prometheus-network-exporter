from jnpr.junos import Device
import re
from cgi import escape, parse_qs
import json
import yaml
import logging
import getpass
from prometheus_junos_exporter import wrapping
from prometheus_junos_exporter import custom_junos as junos
import os
logger = logging.getLogger(__name__)

wrapping.init()
config = None


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

    def register(self, name, metric_type):
        """
        Add a metric to the registry
        """
        if self._metrics_registry.get(name) is None:
            self._metrics_registry[name] = []
            self._metric_types[name] = metric_type
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
            lines.append("# TYPE {} {}".format(name, metric_type))
            lines.extend(self._metrics_registry[name])
        return "\n".join([str(x) for x in lines]) + '\n'


def hello(environ, start_response):
    """Like the example above, but it uses the name specified in the
URL."""
    # get the name from the url if it was specified there.
    args = environ['myapp.url_args']
    if args:
        subject = escape(args[0])
    else:
        subject = 'World'
    start_response('200 OK', [('Content-Type', 'text/html')])
    return ['''Hello %(subject)s
            Hello %(subject)s!

''' % {'subject': subject}]


def not_found(environ, start_response):
    """Called if no URL matches."""
    start_response('404 NOT FOUND', [('Content-Type', 'text/plain')])
    return [bytes('Not Found', 'utf-8')]


def get_interface_metrics(registry, dev, hostname, access=True):
    """
    Get interface metrics
    """
    # interfaces
    interfaces = {}
    if access:
        interfaces = junos.get_specific_ports_information(
            dev, ["[gxe][et]-*/1/*"])
    else:
        interfaces = junos.get_all_ports_information(dev)

    for MetricName, MetricFamily in wrapping.METRICS.items():
        for metrik_def in wrapping.NETWORK_METRICS.get(MetricName, []):
            metrik_name, key, function, _ = wrapping.create_metrik_params(
                metrik_def)
            metrik_name = "{}_{}_{}".format(wrapping.METRICS_BASE.get(
                'base', 'junos'), wrapping.METRICS_BASE.get('interface', 'interface'), metrik_name)
            registry.register(metrik_name, MetricFamily)
            for interface, metriken in interfaces.items():
                if metriken.get(key) is not None:
                    labels_data = {'hostname': hostname,
                                   'interface': interface}
                    labels_variable = {label['key']: metriken.get(
                        label['key'], "") for label in wrapping.NETWORK_LABEL_WRAPPER}
                    labels = {**labels_data, **labels_variable}
                    wrapping.create_metrik(metrik_name,
                                           registry, key, labels, metriken, function=function)


def get_environment_metrics(registry, dev, hostname):
    """
    Get environment metrics
    """
    environment = junos.get_environment(dev)
    for MetricName, MetricFamily in wrapping.METRICS.items():
        for metrik_def in wrapping.ENVIRONMENT_METRICS.get(MetricName, []):
            metrik_name, key, function, specific = wrapping.create_metrik_params(
                metrik_def)
            metrik_name = "{}_{}_{}".format(
                wrapping.METRICS_BASE['base'], wrapping.METRICS_BASE['device'], metrik_name)
            registry.register(metrik_name, MetricFamily)
            labels_data = {'hostname': hostname}
            labels_variable = {label['key']: environment.get(
                label['key'], "") for label in wrapping.ENVIRONMENT_LABEL_WRAPPER}
            labels = {**labels_data, **labels_variable}
            if specific and function:
                data = environment.get(key, None)
                wrapping.FUNCTIONS[function](
                    metrik_name, registry, labels, data, create_metrik=wrapping.create_metrik)
            elif environment.get(key):
                wrapping.create_metrik(
                    metrik_name, registry, key, labels, environment, function=function)
    print("Change all metrics")


def get_bgp_metrics(registry, dev, hostname):
    """
    Get BGP neighbor metrics
    """
    bgp = junos.get_bgp_information(dev)
    for MetricName, MetricFamily in wrapping.METRICS.items():
        for metrik_def in wrapping.BGP_METRICS.get(MetricName, []):
            metrik_name, key, function, specific = wrapping.create_metrik_params(
                metrik_def)
            metrik_name = "{}_{}_{}".format(
                wrapping.METRICS_BASE['base'], wrapping.METRICS_BASE['bgp'], metrik_name)
            registry.register(metrik_name, MetricFamily)
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


def metrics(environ, start_response):

    # load config
    CONF_DIR = os.path.join('/etc', 'prometheus-junos-exporter')
    with open(os.path.join(CONF_DIR, 'config.yml'), 'r') as f:
        config = yaml.load(f)

    # parameters from url
    parameters = parse_qs(environ.get('QUERY_STRING', ''))

    # get profile from config
    profile = config[parameters.get('module', ['default'])[0]]
    hostname = parameters['target'][0]
    # open device connection
    if profile['auth']['method'] == 'password':
        # using regular username/password
        dev = Device(host=hostname,
                     user=profile['auth'].get('username', getpass.getuser()),
                     password=profile['auth'].get('password', getpass.getpass()),
                     port=profile['auth'].get('port', 22))
    elif profile['auth']['method'] == 'ssh_key':
        # using ssh key
        dev = Device(host=hostname,
                     user=profile['auth'].get('username', getpass.getuser()),
                     ssh_private_key_file=profile['auth'].get(
                         'ssh_key', '~/.ssh/id_rsa'),
                     port=profile['auth'].get('port', 22),
                     password=profile['auth'].get('password', None))
    dev.open()
    # create metrics registry
    registry = Metrics()

    # get and parse metrics
    types = profile['metrics']
    if 'interface' in types:
        get_interface_metrics(registry, dev, hostname, access=False)
    if 'interface_specifics' in types:
        get_interface_metrics(registry, dev, hostname, access=True)
    if 'environment' in types:
        get_environment_metrics(registry, dev, hostname)
    if 'bgp' in types:
        get_bgp_metrics(registry, dev, hostname)

    # start response
    data = registry.collect()
    status = '200 OK'
    response_headers = [
        ('Content-type', 'text/plain')
    ]
    start_response(status, response_headers)
    return [bytes(data, 'utf-8')]


# map urls to functions
urls = [
    # (r'metrics$', self_service),
    # (r'metrics/$', self_service),
    (r'metrics/?$', metrics),
    (r'metrics/(.+)$', metrics)
]


def app(environ, start_response):
    """
    The main WSGI application. Dispatch the current request to
    the functions from above and store the regular expression
    captures in the WSGI environment as  `myapp.url_args` so that
    the functions from above can access the url placeholders.

    If nothing matches call the `not_found` function.
    """
    path = environ.get('PATH_INFO', '').lstrip('/')
    for regex, callback in urls:
        match = re.search(regex, path)
        if match is not None:
            environ['app.url_args'] = match.groups()
            return callback(environ, start_response)
    return not_found(environ, start_response)
