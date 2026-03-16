from prometheus_network_exporter.devices import basedevice


class HuaweiNeworkDevice(basedevice.Device):
    def __init__(
        self,
        hostname,
        user=None,
        password=None,
        port=22,
        ssh_private_key_file=None,
        ssh_config=None,
        **kwargs
    ):
        pass
