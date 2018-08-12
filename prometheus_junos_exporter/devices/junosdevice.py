
'''
    General Device 
'''
from pprint import pprint
from jnpr.junos import Device
from jnpr.junos.exception import RpcError, ConnectError
from prometheus_junos_exporter.devices import basedevice
from prometheus_junos_exporter.views.junos.optic import PhyPortDiagTable
from prometheus_junos_exporter.views.junos.interface_metrics import MetricsTable
from prometheus_junos_exporter.views.junos.bgp import BGPNeighborTable
from prometheus_junos_exporter.views.junos.environment import RoutingEngineTable, EnvironmentTable
from prometheus_junos_exporter.views.junos.ospf import OspfNeighborTable, Ospf3NeighborTable


class JuniperNetworkDevice(basedevice.NetworkDevice):
    def __init__(self, host, user=None, password=None, port=22, ssh_private_key_file=None, ssh_config=None):
        device = Device(host=host,
                        user=user,
                        ssh_private_key_file=ssh_private_key_file,
                        ssh_config=ssh_config,
                        password=password,
                        port=port)
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
            if ospf:
                ospf = self.get_ospf()
            else:
                ospf = {}
            for port in ports.keys():
                result[port] = {**ports[port], **
                                intopticdiag.get(port, {}), **ospf.get(port, {})}
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
                if ospf:
                    ospf = self.get_ospf(interface_name=interface_name)
                else:
                    ospf = {}
                for port in ports.keys():
                    result[port] = {**ports[port], **
                                    intopticdiag.get(port, {}), **ospf.get(port, {})}
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
        result = {}
        ospf = dict(OspfNeighborTable(self.device).get()) if interface_name is None else dict(
            OspfNeighborTable(self.device).get(interface_name=interface_name))
        ospf3 = dict(Ospf3NeighborTable(self.device).get()) if interface_name is None else dict(
            Ospf3NeighborTable(self.device).get(interface_name=interface_name))
        for interface_name in ospf.keys():
            splitted_name = interface_name.split('.')
            interface = splitted_name[0]
            unit = int(splitted_name[1])
            if interface not in result.keys():
                result[interface] = {}
            result[interface]['ospf'] = {unit: dict(ospf.get(interface_name, {}))}
            result[interface]['ospf3'] = {unit: dict(ospf3.get(interface_name, {}))}
        return result

    def get_optics(self, interface_name=None):
        return dict(PhyPortDiagTable(self.device).get()) if interface_name is None else dict(
            PhyPortDiagTable(self.device).get(interface_name=interface_name))

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
        if self.is_connected():
            self.device.close()
        return self.is_connected()
