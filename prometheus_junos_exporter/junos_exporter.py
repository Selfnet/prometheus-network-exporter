#!/usr/bin/env python3
import sys
import os
import multiprocessing
import time
import datetime
from getpass import getpass, getuser
import yaml
from threading import Thread
from jnpr.junos import Device
import prometheus_junos_exporter.custom_junos as junos
from pprint import pprint
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily

CONF_DIR = os.path.join('/etc', 'prometheus-junos-exporter')
try:
    with open(os.path.join(CONF_DIR, 'config.yml'), 'r') as connection_definitions:
        CONFIG = yaml.load(connection_definitions)
except FileNotFoundError:
    print("No config under: {}\n\tUsing default!".format(CONF_DIR))

if not CONFIG:
    CONFIG = {}


# If u want to have more metrics. You must edit the config/metrics_definitions.yml
with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config', 'metrics_definition.yml'), 'r') as metrics_definitions:
    DEFINITIONS = yaml.load(metrics_definitions).get('DEFINITIONS', {})
# This is a sample for a connection.
# You must specify a password or keyfile under config/config.yml
CONNECTIONS = CONFIG.get('CONNECTIONS', {})

CONNECTION_SSH = CONNECTIONS.get('ssh', {})
USERNAME = CONNECTION_SSH.get('USERNAME', getuser())
PRIV_KEYFILE = CONNECTION_SSH.get('PRIV_KEYFILE', None)
CONFIG_FILE = CONNECTION_SSH.get('CONFIG_FILE', '~/.ssh/config')
KEEPALIVE = CONNECTION_SSH.get('KEEPALIVE', 30)
TIMEOUT = CONNECTION_SSH.get('TIMEOUT', 300)
NETCONF_PORT = CONNECTION_SSH.get('NETCONF_PORT', 830)

if not PRIV_KEYFILE:
    PASSWORD = getpass(prompt="SSH_PASSWORD:")
else:
    PASSWORD = None

# Get the Metrics DEFINITIONS
METRICS_BASE = DEFINITIONS.get('METRICS_BASE', {})
NETWORK_REGEXES = DEFINITIONS.get('NETWORK_REGEXES', [])
NETWORK_METRICS = DEFINITIONS.get('NETWORK_METRICS', {})
ENVIRONMENT_METRICS = DEFINITIONS.get('ENVIRONMENT_METRICS', {})
NETWORK_LABEL_WRAPPER = DEFINITIONS.get('NETWORK_LABEL_WRAPPER', [])
ENVIRONMENT_LABEL_WRAPPER = DEFINITIONS.get('ENVIRONMENT_LABEL_WRAPPER', [])
BGP_METRICS = DEFINITIONS.get('BGP_METRICS', {})
BGP_LABEL_WRAPPER = DEFINITIONS.get('BGP_LABEL_WRAPPER', [])

# TEMP Storage Variable
RESULTS = {}


def start_loop(function, hostname, access, function_name):
    global RESULTS
    RESULTS[function_name].append(function(hostname, access))


def is_ok(boolean):
    if isinstance(boolean, bool):
        if boolean:
            return 1
        return 0
    elif isinstance(boolean, str):
        if boolean.lower() in ['up', 'ok', 'established']:
            return 1
        return 0
    else:
        raise Exception("Unknown Type")


def flap(string):
    if 'never' in string.lower():
        return 0
    string = string.split(" (")[0]
    val = time.mktime(datetime.datetime.strptime(
        string, "%Y-%m-%d %H:%M:%S %Z").timetuple())
    return val


def temp(string):
    string = int(string.split(' ')[0])
    return string


def intify(string):
    return int(string)


def floatify(string):
    return float(string)


def boolify(string):
    return 'true' in string.lower()


def fan_power_temp_status(metrik, labels, data, create_metrik=None):
    for sensorname, information in data.items():
        labels.append(sensorname)
        metrik = create_metrik(metrik, 'status', labels,
                               information, function='is_ok')
        labels.remove(sensorname)
    return metrik


def temp_celsius(metrik, labels, data, create_metrik=None):
    for sensorname, information in data.items():
        labels.append(sensorname)
        metrik = create_metrik(metrik, 'temperature',
                               labels, information, function='intify')
        labels.remove(sensorname)
    return metrik


def reboot(metrik, labels, data, create_metrik=None):
    reason_string = data['last_reboot_reason']
    reason = 1
    if "failure" in reason_string:
        reason = 0
    else:
        reason = 1
    labels.append(reason_string)
    metrik.add_metric(labels, reason)
    return metrik


def cpu_usage(metrik, labels, data, create_metrik=None):
    for slot, perf in data.items():
        label = "cpu_{}".format(str(slot))
        labels.append(label)
        cpu_usage = 100 - int(perf['cpu-idle'])
        metrik.add_metric(labels, cpu_usage)
        labels.remove(label)
    return metrik


def cpu_idle(metrik, labels, data, create_metrik=None):
    for slot, perf in data.items():
        label = "cpu_{}".format(str(slot))
        labels.append(label)
        cpu_idle = int(perf['cpu-idle'])
        metrik.add_metric(labels, cpu_idle)
        labels.remove(label)
    return metrik


def ram_usage(metrik, labels, data, create_metrik=None):
    for slot, perf in data.items():
        label = "ram_{}".format(str(slot))
        labels.append(label)
        memory_complete = perf['memory-dram-size'].lower().replace("mb",
                                                                   "").strip()
        memory_complete = int(memory_complete)
        memory_usage = int(perf['memory-buffer-utilization'])
        memory_bytes_usage = (memory_complete * memory_usage / 100) * 1049000
        metrik.add_metric(labels, memory_bytes_usage)
        labels.remove(label)
    return metrik


def ram(metrik, labels, data, create_metrik=None):
    for slot, perf in data.items():
        label = "ram_{}".format(str(slot))
        labels.append(label)
        memory_complete = perf['memory-dram-size'].lower().replace("mb",
                                                                   "").strip()
        memory_complete = int(memory_complete)
        memory_bytes = memory_complete * 1049000
        metrik.add_metric(labels, memory_bytes)
        labels.remove(label)
    return metrik


FUNCTIONS = {
    'is_ok': is_ok,
    'flap': flap,
    'temp': temp,
    'intify': intify,
    'floatify': floatify,
    'fan_power_temp_status': fan_power_temp_status,
    'temp_celsius': temp_celsius,
    'reboot': reboot,
    'cpu_idle': cpu_idle,
    'cpu_usage': cpu_usage,
    'ram': ram,
    'ram_usage': ram_usage
}

METRICS = {
    'Counter': CounterMetricFamily,
    'Gauge': GaugeMetricFamily
}


class JunosCollector(object):
    def __init__(self, hostnames, access):

        self.hostnames = hostnames
        self.access = [boolify(att) for att in access]

    def _get_metrics(self):
        global RESULTS
        RESULTS['hosts'] = []
        result = []
        for hostname, access in zip(self.hostnames, self.access):
            t = Thread(target=start_loop, args=(
                self._get_metric, hostname, access, 'hosts'))
            result.append(t)
            t.start()
        [t.join() for t in result]

        return RESULTS['hosts']

    def _get_metric(self, hostname, access):
        dev_info = {}
        with Device(host=hostname, username=USERNAME, password=PASSWORD, port=NETCONF_PORT, ssh_private_key_file=PRIV_KEYFILE, ssh_config=CONFIG_FILE) as dev:
            dev.timeout = TIMEOUT
            dev_info[hostname] = {}
            dev_info[hostname]['interfaces'] = {}
            dev_info[hostname]['environment'] = {}
            dev_info[hostname]['bgp'] = {}
            try:
                if access:
                    dev_info[hostname]['interfaces'] = junos.get_specific_ports_information(
                        dev, interface_junos_notations=NETWORK_REGEXES)
                else:
                    dev_info[hostname]['interfaces'] = junos.get_all_ports_information(
                        dev)
            except Exception as e:
                print(e)
                print("{} ::: get no Interface Data".format(hostname))
            try:
                dev_info[hostname]['environment'] = junos.get_environment(dev)
            except Exception as e:
                print(e)
                print("{} ::: get no Environment Data".format(hostname))
            try:
                dev_info[hostname]['bgp'] = junos.get_bgp_information(dev)
            except Exception as e:
                print(e)
                print("{} ::: get no BGP Information".format(hostname))
        return dev_info

    def create_metrik_params(self, metrik_def, call='interfaces'):
        metrik_name = metrik_def['metrik']
        key = metrik_def['key']
        description = metrik_def.get('description', '')
        type_of = metrik_def.get('type', None)
        function = metrik_def.get('function', None)
        specific = metrik_def.get('specific', False)
        labels = ['hostname']
        if type_of:
            metrik_name = '{}_{}'.format(metrik_name, type_of)
        if 'interfaces' in call:
            labels.append('interface')
            [labels.append(label['label']) for label in NETWORK_LABEL_WRAPPER]
        elif 'bgp' in call:
            labels.append('description')
            [labels.append(label['label']) for label in BGP_LABEL_WRAPPER]

        [labels.append(label['label'])
         for label in ENVIRONMENT_LABEL_WRAPPER]
        if specific:
            labels.append("name")
        return metrik_name, key, description, function, labels, specific

    def create_metrik(self, metrik, key, labels, metriken, function=None):
        if metriken.get(key) is not None:
            try:
                if function:
                    metrik.add_metric(
                        labels, FUNCTIONS[function](metriken.get(key)))
                else:
                    metrik.add_metric(
                        labels, metriken.get(key))
            except (ValueError, KeyError) as e:
                print("Error :: {}".format(e))
        return metrik

    def describe(self):
        return []

    def collect(self):
        global FUNCTIONS
        metrics_data = self._get_metrics()
        metrics = []
        for MetricName, MetricFamily in METRICS.items():

            # hosts_interfaces = self.extract_interfaces(metrics_data)
            # hosts_environments = self.extract_environment(metrics_data)
            # INTERFACE Information
            # {'hostname.fqdn':
            #   'xe-0/1/1': {
            #        'admin': 'up',
            #        'description': 'Core: ar1-8b-1',
            #        'flapped': '2017-08-07 09:50:47 CEST '
            #                    '(33w2d 11:14 ago)',
            #        'link_mode': None,
            #        'macaddr': '40:b4:f0:72:fa:5c',
            #        'module_temperature': '48 degrees C '
            #                            '/ 119 degrees '
            #                            'F',
            #        'module_voltage': '3.3170',
            #        'mtu': 1514,
            #        'oper': 'up',
            #        'present': True,
            #        'running': True,
            #        'rx_bytes': 7694149952049,
            #        'rx_err_discards': 0,
            #        'rx_err_drops': 0,
            #        'rx_err_fifo': 0,
            #        'rx_err_frame': 0,
            #        'rx_err_input': 0,
            #        'rx_err_l2-channel': 0,
            #        'rx_err_l2-mismatch': 0,
            #        'rx_err_l3-incompletes': 0,
            #        'rx_err_resource': 0,
            #        'rx_err_runts': 0,
            #        'rx_optic_power': '-2.02',
            #        'rx_packets': 6886830321,
            #        'speed': '10Gbps',
            #        'tx_bytes': 3354214934381,
            #        'tx_err_aged': 0,
            #        'tx_err_carrier-transitions': 5,
            #        'tx_err_collisions': 0,
            #        'tx_err_drops': 0,
            #        'tx_err_fifo': 0,
            #        'tx_err_hs-crc': 0,
            #        'tx_err_mtu': 0,
            #        'tx_err_output': 0,
            #        'tx_err_resource': 0,
            #        'tx_optic_power': '-2.68',
            #        'tx_packets': 4280648959},
            #   ...
            # }

            for metrik_def in NETWORK_METRICS.get(MetricName, []):
                metrik_name, key, description, function, labels, _ = self.create_metrik_params(
                    metrik_def)
                metrik = MetricFamily("{}_{}_{}".format(
                    METRICS_BASE['base'], METRICS_BASE['interface'], metrik_name), description, labels=labels)
                for host in metrics_data:
                    for hostname, data in host.items():
                        for interface, metriken in data['interfaces'].items():
                            if metriken.get(key) is not None:
                                labels = [hostname, interface]
                                [labels.append(metriken.get(label['key'])) if metriken.get(
                                    label['key']) else labels.append("") for label in NETWORK_LABEL_WRAPPER]
                                [labels.append(data['environment'].get(label['key'])) if data.get('environment').get(
                                    label['key']) else labels.append("") for label in ENVIRONMENT_LABEL_WRAPPER]
                                metrik = self.create_metrik(
                                    metrik, key, labels, metriken, function=function)
                metrics.append(metrik)

        # ENVIRONMENT Information
        # {'hostname.fqdn.example.com': {
        #     '2RE': False,
        #     'Fans': {'FPC 0 Fan 1': {'class': 'Fans',
        #                                 'status': 'OK',
        #                                 'temperature': None},
        #                 'FPC 0 Fan 2': {'class': 'Fans',
        #                                 'status': 'OK',
        #                                 'temperature': None},
        #                 'FPC 0 Fan 3': {'class': 'Fans',
        #                                 'status': 'OK',
        #                                 'temperature': None},
        #                 'FPC 0 Fan 4': {'class': 'Fans',
        #                                 'status': 'OK',
        #                                 'temperature': None},
        #                 'FPC 0 Fan 5': {'class': 'Fans',
        #                                 'status': 'OK',
        #                                 'temperature': None},
        #                 'FPC 0 Fan-Tray Airflow': {'class': 'Fans',
        #                                         'status': 'OK',
        #                                         'temperature': None}},
        #     'HOME': '/var/home/remote',
        #     'Power': {'FPC 0 Power Supply 0': {'class': 'Power',
        #                                         'status': 'OK',
        #                                         'temperature': None},
        #                 'FPC 0 Power Supply 0 Airflow': {'class': 'Power',
        #                                                 'status': 'OK',
        #                                                 'temperature': None},
        #                 'FPC 0 Power Supply 1': {'class': 'Power',
        #                                         'status': 'OK',
        #                                         'temperature': None},
        #                 'FPC 0 Power Supply 1 Airflow': {'class': 'Power',
        #                                                 'status': 'OK',
        #                                                 'temperature': None}},
        #     'RE0': {'last_reboot_reason': 'Router rebooted '
        #                                     'after a normal '
        #                                     'shutdown.',
        #             'mastership_state': 'master',
        #             'model': 'EX4500-40F',
        #             'status': 'Absent',
        #             'up_time': '471 days, 1 hour, 14 '
        #                         'minutes, 8 seconds'},
        #     'RE1': None,
        #     'RE_hw_mi': False,
        #     'Temp': {'FPC 0 PHY0': {'class': 'Temp',
        #                             'status': 'OK',
        #                             'temperature': 23},
        #                 'FPC 0 PHY12': {'class': 'Temp',
        #                                 'status': 'OK',
        #                                 'temperature': 26},
        #                 'FPC 0 PHY19': {'class': 'Temp',
        #                                 'status': 'OK',
        #                                 'temperature': 27},
        #                 'FPC 0 PHY6': {'class': 'Temp',
        #                             'status': 'OK',
        #                             'temperature': 28},
        #                 'FPC 0 PIC1': {'class': 'Temp',
        #                             'status': 'OK',
        #                             'temperature': 14},
        #                 'FPC 0 PIC2': {'class': 'Temp',
        #                             'status': 'OK',
        #                             'temperature': 15},
        #                 'FPC 0 Rear Left PCB': {'class': 'Temp',
        #                                         'status': 'OK',
        #                                         'temperature': 23},
        #                 'FPC 0 Rear Middle PCB': {'class': 'Temp',
        #                                         'status': 'OK',
        #                                         'temperature': 28},
        #                 'FPC 0 Rear Right PCB': {'class': 'Temp',
        #                                         'status': 'OK',
        #                                         'temperature': 28}},
        #     'current_re': ['master',
        #                     'node',
        #                     'fwdd',
        #                     'member',
        #                     'pfem',
        #                     'fpc0',
        #                     'feb0',
        #                     'fpc16'],
        #     'domain': 'fqdn.example.com',
        #     'fqdn': 'hostname.fqdn.example.com',
        #     'hostname': 'hostname',
        #     'hostname_info': {'fpc0': 'hostname'},
        #     'ifd_style': 'SWITCH',
        #     'junos_info': {'fpc0': {'object': junos.version_info(major=(15, 1), type=R, minor=5, build=5),
        #                             'text': '15.1R5.5'}},
        #     'master': 'RE0',
        #     'model': 'EX4500-40F',
        #     'model_info': {'fpc0': 'EX4500-40F'},
        #     'personality': 'SWITCH',
        #     're_info': {'default': {'0': {'last_reboot_reason': 'Router '
        #                                                         'rebooted '
        #                                                         'after '
        #                                                         'a '
        #                                                         'normal '
        #                                                         'shutdown.',
        #                                     'mastership_state': 'master',
        #                                     'model': 'EX4500-40F',
        #                                     'status': 'Absent'},
        #                             'default': {'last_reboot_reason': 'Router '
        #                                                                 'rebooted '
        #                                                                 'after '
        #                                                                 'a '
        #                                                                 'normal '
        #                                                                 'shutdown.',
        #                                         'mastership_state': 'master',
        #                                         'model': 'EX4500-40F',
        #                                         'status': 'Absent'}}},
        #     're_loads': {'0': {'cpu-idle': 94,
        #                         'memory-buffer-utilization': 77,
        #                         'memory-dram-size': '1024 '
        #                                             'MB'}},
        #     're_master': {'default': '0'},
        #     'serialnumber': 'GX0211344527',
        #     'srx_cluster': None,
        #     'srx_cluster_id': None,
        #     'srx_cluster_redundancy_group': None,
        #     'switch_style': 'VLAN',
        #     'uptime': 40698851,
        #     'vc_capable': True,
        #     'vc_fabric': False,
        #     'vc_master': '0',
        #     'vc_mode': 'Enabled',
        #     'version': '15.1R5.5',
        #     'version_RE0': None,
        #     'version_RE1': None,
        #     'version_info': junos.version_info(major=(15, 1), type=R, minor=5, build=5),
        #     'virtual': False}}

            for metrik_def in ENVIRONMENT_METRICS.get(MetricName, []):
                metrik_name, key, description, function, labels, specific = self.create_metrik_params(
                    metrik_def, call="device")
                metrik = MetricFamily("{}_{}_{}".format(
                    METRICS_BASE['base'], METRICS_BASE['device'], metrik_name), description, labels=labels)
                for host in metrics_data:
                    for hostname, data in host.items():
                        environment = data.get('environment', None)
                        if environment:
                            labels = [hostname]
                            [labels.append(environment.get(label['key'])) if environment.get(
                                label['key']) else labels.append("") for label in ENVIRONMENT_LABEL_WRAPPER]
                            if specific and function:
                                data = environment.get(key, None)
                                metrik = FUNCTIONS[function](
                                    metrik, labels, data, create_metrik=self.create_metrik)
                            elif environment.get(key):
                                metrik = self.create_metrik(
                                    metrik, key, labels, environment, function=function)
                metrics.append(metrik)
        # BGP Information
        # {'hostname.example.com':
        #     {'bgp':
        #         {'reverse.peearadr.example.com':
        #             {'description': None,
        #             'peeraddr': '::d',
        #             'peerstate': 'Established',
        #             'pfx_rx': '60'},
        #         'reverse.peearadr2.example.com':
        #             {'description': None,
        #             'peeraddr': '::f',
        #             'peerstate': 'Established',
        #             'pfx_rx': '60'},
        #         'reverse.peearadr3.example.com':
        #         {'description': None,
        #         'peeraddr': '::2',
        #         'peerstate': 'Established',
        #         'pfx_rx': '60'}}
        #     }
        # }

            for metrik_def in BGP_METRICS.get(MetricName, []):
                metrik_name, key, description, function, labels, specific = self.create_metrik_params(
                    metrik_def, call='bgp')
                metrik = MetricFamily("{}_{}_{}".format(
                    METRICS_BASE['base'], METRICS_BASE['bgp'], metrik_name), description, labels=labels)
                for host in metrics_data:
                    for hostname, data in host.items():
                        bgp = data.get('bgp', None)
                        if bgp:
                            for peername, metriken in bgp.items():
                                if metriken.get(key) is not None:
                                    labels = [hostname, peername]
                                    [labels.append(metriken.get(label['key'])) if metriken.get(
                                        label['key']) else labels.append("") for label in BGP_LABEL_WRAPPER]
                                    [labels.append(data['environment'].get(label['key'])) if data.get('environment').get(
                                        label['key']) else labels.append("") for label in ENVIRONMENT_LABEL_WRAPPER]
                                    metrik = self.create_metrik(
                                        metrik, key, labels, metriken, function=function)
                metrics.append(metrik)

        for metrik in metrics:
            yield metrik
        print("Done for {}".format(self.hostnames))
