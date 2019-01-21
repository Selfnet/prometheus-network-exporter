from prometheus_network_exporter.devices import basedevice


class CiscoNetworkDevice(basedevice.Device):
    pass


class CiscoMetrics(basedevice.Metrics):
    def __init__(self, *args, **kwargs):
        super(CiscoMetrics, self).__init__(*args, **kwargs)
    def metrics(self, types, dev, registry):
        pass
