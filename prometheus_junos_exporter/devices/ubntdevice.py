
'''
    General Device 
'''
from pprint import pprint
import json
from unifi_client import AirMaxAPIClient
from prometheus_junos_exporter.config.definitions.unifi import wrapping
from prometheus_junos_exporter.devices import basedevice
from prometheus_junos_exporter.utitlities import create_metric, create_metric_params, FUNCTIONS, METRICS


class AirMaxDevice(basedevice.Device):
    def __init__(self, hostname, username=None, password=None, port=443, proxy=None, verify=False, protocol='https'):
        device = AirMaxAPIClient(
            username=username, password=password, url='{protocol}://{hostname}:{port}'.format(
                protocol=protocol, hostname=hostname, port=port), proxy=proxy, verify=verify)
        super().__init__(hostname, device)
        self.statistics = None

    def is_connected(self):
        try:
            self.device.statistics()
        except:
            return False
        return True

    def connect(self):
        self.device.login()

    def disconnect(self):
        self.device.logout()

    def init(self):
        self.statistics = self.device.statistics()


class AirMaxMetrics(object):

    def get_interface_metrics(self, registry, dev, hostname):
        interfaces = dev.statistics.get("interfaces", {})

        for MetricName, MetricFamily in METRICS.items():
            for metric_def in wrapping.NETWORK_METRICS.get(MetricName, []):
                metric_name, description, key, function, _ = create_metric_params(
                    metric_def)
                metric_name = "{}_{}_{}".format(wrapping.METRICS_BASE.get(
                    'base', 'junos'), wrapping.METRICS_BASE.get('interface', 'interface'), metric_name)
                registry.register(metric_name, description, MetricFamily)
                for interface in interfaces:
                    interface_name = interface.get('ifname', "unknown")
                    mac = interface.get("hwaddr")
                    metrics = interface.get('status')
                    if metrics.get(key) is not None:
                        labels_data = {'interface': interface_name,
                                       'mac': mac}
                        labels_variable = {label['label']: metrics.get(
                            label['key'], "") for label in wrapping.NETWORK_LABEL_WRAPPER}
                        labels = {**labels_data, **labels_variable}
                        create_metric(metric_name,
                                      registry, key, labels, metrics, function=function)

    def get_wireless_metrics(self, registry, dev, hostname):
        wireless = dev.statistics.get("wireless", {})
        polling = wireless.get('polling', {})
        sta = wireless.get('sta', [{}])
        airmax = sta[0].get('airmax', {})
        stats = sta[0].get('stats', {})
        tx = sta[0].get('tx', {})
        rx = sta[0].get('rx', {})
        



    def get_host_information(self, registry, dev, hostname):
        host = dev.statistics.get("host", {})
        metrics = host
        for MetricName, MetricFamily in METRICS.items():
            for metric_def in wrapping.ENVIRONMENT_METRICS.get(MetricName, []):
                metric_name, description, key, function, _ = create_metric_params(
                    metric_def)
                metric_name = "{}_{}_{}".format(wrapping.METRICS_BASE.get(
                    'base', 'junos'), wrapping.METRICS_BASE.get('device', 'device'), metric_name)
                registry.register(metric_name, description, MetricFamily)
                if metrics.get(key) is not None:
                    labels = None
                    create_metric(metric_name,
                                    registry, key, labels, metrics, function=function)

    def metrics(self, types, dev, registry):
        try:
            dev.connect()
            dev.init()
            if 'interface' in types:
                self.get_interface_metrics(registry, dev, dev.hostname)
            if 'wireless statistics' in types:
                self.get_wireless_metrics(registry, dev, dev.hostname)
            if 'environment' in types:
                self.get_host_information(registry, dev, dev.hostname)
        except Exception as e:
            print(e)
            return 500, "Device unreachable", "Device {} unreachable".format(dev.hostname)
        dev.disconnect()
        return 200, "OK", registry.collect()


if __name__ == '__main__':
    pass
