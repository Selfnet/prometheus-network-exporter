from prometheus_junos_exporter.devices import basedevice


class CiscoNetworkDevice(basedevice.Device):
    pass


class CiscoMetrics(basedevice.Metrics):
    def metrics(self, types, dev, registry):
        pass
