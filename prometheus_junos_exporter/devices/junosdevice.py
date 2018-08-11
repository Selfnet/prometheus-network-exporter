
'''
    General Device 
'''
import socket
from jnpr.junos import Device
from jnpr.junos.exception import RpcError, ConnectError
from prometheus_junos_exporter.devices import basedevice
from prometheus_junos_exporter.views.junos.optic import PhyPortDiagTable
from prometheus_junos_exporter.views.junos.interface_metrics import MetricsTable
from prometheus_junos_exporter.views.junos.bgp import BGPNeighborTable
from prometheus_junos_exporter.views.junos.environment import RoutingEngineTable, EnvironmentTable
from prometheus_junos_exporter.views.junos.ospf import OspfNeighborTable, Ospf3NeighborTable


class JuniperNetworkDevice(basedevice.NetworkDevice):
    def __init__(self, device):
        super().__init__(device)

    def get_bgp(self):
        try:
            bgp = dict(BGPNeighborTable(self.device).get())
        except RpcError:
            return {}
        return {self.lookup(k): dict(v) for k, v in bgp.items()}

    def get_interface(self, interface_names=None, ospf=False, optics=False):
        result = {}
        if not interface_names:
            ports = dict(MetricsTable(self.device).get())
            if optics:
                intopticdiag = self.get_optics()
            else:
                intopticdiag = {}
            for port in ports.keys():
                result[port] = {**ports[port], **intopticdiag.get(port, {})}
        else:
            for interface_name in interface_names:
                print(interface_name)
                ports = dict(MetricsTable(self.device).get(
                    interface_name=interface_name))
                if optics:
                    intopticdiag = self.get_optics(
                        interface_name=interface_name)
                else:
                    intopticdiag = {}
                for port in ports.keys():
                    result[port] = {**ports[port], **
                                    intopticdiag.get(port, {})}
        return result

    def get_environment(self):
        facts = self.device.facts
        uptime = self.device.uptime
        rengine = RoutingEngineTable(self.device).get()
        temperatures = EnvironmentTable(self.device).get()
        return {
            **facts,
            **{'uptime': uptime},
            **{'re_loads': {k: dict(v) for k, v in rengine.items()}},
            **{'Temp': {k: dict(v) for k, v in temperatures.items() if 'Temp' == dict(v)['class']}},
            **{'Fans': {k: dict(v) for k, v in temperatures.items() if 'Fans' == dict(v)['class']}},
            **{'Power': {k: dict(v) for k, v in temperatures.items() if 'Power' == dict(v)['class']}}
        }

    def get_ospf(self, interface_name=None):
        return dict(OspfNeighborTable(self.device).get())

    def get_optics(self, interface_name=None):
        return dict(PhyPortDiagTable(self.device).get()) if interface_name is None else dict(PhyPortDiagTable(self.device).get(interface_name=interface_name))

    def is_connected(self):
        return self.device.connected

    def connect(self):
        if self.is_connected():
            return True
        try:
            self.device.open()
            return True
        except ConnectError as err:
            print(err)
        return False

    def disconnect(self):
        if self.is_connected:
            self.device.close()
