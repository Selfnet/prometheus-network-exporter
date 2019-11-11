
import yaml
from ..base import Collector
from . import base
from prometheus_network_exporter.devices.basedevice import Device


class InterfaceCollector(Collector):

    default = yaml.loads(
        __loader__.get_resource_reader(
            __name__
        ).open_resource(
            'interface.yaml'
        ),
        loader=yaml.SafeLoader
    )
    name = 'interface'
    base_name = "{0}_{1}".format(base, name)

    def __init__(
            self,
            device: Device,
            access: bool = False,
            ospf: bool = False,
            optics: bool = False,
            config_path: str = None
    ):
        self.access = access
        self.ospf = ospf
        self.optics = optics
        config = self.default
        if config_path is not None:
            with open(config_path, 'r') as file:
                config = yaml.load(file, loader=yaml.SafeLoader)
        super.__init__(InterfaceCollector, self).__init__(self.base_name, device, config=config)
        self._init_prometheus_metrics()

    def collect(self):
        yield
        pass
