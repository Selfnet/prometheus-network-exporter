
'''
    General Device 
'''

from unifi_client import AirMaxAPIClient
from prometheus_network_exporter.config.definitions.unifi import wrapping
from prometheus_network_exporter.devices import basedevice
from prometheus_network_exporter.utitlities import create_metric, create_metric_params, FUNCTIONS, METRICS, flatten


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


class AirMaxMetrics(basedevice.Metrics):
    def __init__(self, *args, **kwargs):
        super(AirMaxMetrics, self).__init__(*args, **kwargs)

    def get_interface_metrics(self, registry, dev):
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

    def get_wireless_metrics(self, registry, dev):
        wireless = dev.statistics.get("wireless", {})
        polling = wireless.get('polling', {})
        self._get_wireless_metrics(
            polling, wrapping.POLLING_METRICS, registry, dev)
        sta = wireless.get('sta', [{}])
        self._get_wireless_metrics(
            sta[0], wrapping.STATION_METRICS, registry, dev)
        stats = sta[0].get('stats', {})
        self._get_wireless_metrics(
            stats, wrapping.STATS_METRICS, registry, dev)
        airmax = flatten(sta[0].get('airmax', {}))
        self._get_wireless_metrics(
            airmax, wrapping.AIRMAX_METRICS, registry, dev)

    def _get_wireless_metrics(self, metrics, definitions, registry, dev):
        for MetricName, MetricFamily in METRICS.items():
            for metric_def in definitions.get(MetricName, []):
                metric_name, description, key, function, _ = create_metric_params(
                    metric_def)
                metric_name = "{}_{}_{}".format(wrapping.METRICS_BASE.get(
                    'base', 'junos'), wrapping.METRICS_BASE.get('wireless', 'wireless'), metric_name)
                registry.register(metric_name, description, MetricFamily)
                if metrics.get(key) is not None:
                    labels = None
                    create_metric(metric_name,
                                  registry, key, labels, metrics, function=function)

    def get_host_information(self, registry, dev):
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
                self.get_interface_metrics(registry, dev)
            if 'wireless statistics' in types:
                self.get_wireless_metrics(registry, dev)
            if 'environment' in types:
                self.get_host_information(registry, dev)
        except Exception as e:
            print(e)
            return 500, "Device unreachable", "Device {} unreachable".format(dev.hostname)
        dev.disconnect()
        return 200, "OK", registry.collect()


if __name__ == '__main__':
    pass
