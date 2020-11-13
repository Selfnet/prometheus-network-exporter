'''
    General Device
'''

from __future__ import annotations

from jnpr.junos import Device
from jnpr.junos.exception import RpcError, ConnectAuthError, RpcTimeoutError
from ncclient.transport.errors import AuthenticationError
from prometheus_client import generate_latest

from prometheus_network_exporter.collectors.junos.bgp import BGPCollector
from prometheus_network_exporter.collectors.junos.environment import \
    EnvironmentCollector
from prometheus_network_exporter.collectors.junos.igmp import IGMPCollector
from prometheus_network_exporter.collectors.junos.interface import \
    InterfaceCollector
from prometheus_network_exporter.devices import basedevice
from prometheus_network_exporter.views.junos.bgp import BGPNeighborTable
from prometheus_network_exporter.views.junos.environment import (
    EnvironmentTable, RoutingEngineTable, SoftwareTable)
from prometheus_network_exporter.views.junos.igmp import IGMPGroupTable
from prometheus_network_exporter.views.junos.interface_metrics import \
    MetricsTable
from prometheus_network_exporter.views.junos.optic import PhyPortDiagTable
from prometheus_network_exporter.views.junos.ospf import (Ospf3NeighborTable,
                                                          OspfNeighborTable)

from ..config.junos import OSPFType


class JuniperNetworkDevice(basedevice.Device):
    def __init__(
        self,
        hostname,
        user=None,
        password=None,
        port=22,
        ssh_private_key_file=None,
        ssh_config=None,
        **kwargs
    ) -> JuniperNetworkDevice:
        device = Device(
            host=hostname,
            user=user,
            ssh_private_key_file=ssh_private_key_file,
            ssh_config=ssh_config,
            password=password,
            port=port,
            gather_facts=False,
            fact_style='old'
        )
        super(JuniperNetworkDevice, self).__init__(hostname, device, **kwargs)
        self.register_collectors(self.types)

    def register_collectors(self, types: list):
        ospf = True
        optics = True
        if 'ospf' not in types:
            ospf = False
        if 'optics' not in types:
            optics = False
        if 'interface' in types and 'interface_specifics' not in types:
            self.registry.register(InterfaceCollector(self, ospf=ospf, optics=optics))
        if 'interface_specifics' in types and 'interface' not in types:
            self.registry.register(InterfaceCollector(self, access=True, ospf=ospf, optics=optics))
        if 'environment' in types:
            self.registry.register(EnvironmentCollector(self))
        if 'bgp' in types:
            self.registry.register(BGPCollector(self))
        if 'igmp' in types:
            self.registry.register(IGMPCollector(self))

    def get_bgp(self):
        try:
            bgp = dict(BGPNeighborTable(self.device).get())
        except RpcError:
            return {}
        bgp = {k: dict(v) for k, v in bgp.items()}
        for information in bgp.values():
            information['peername'] = self.lookup(information['peerid'])
        return bgp

    def get_interfaces(self, interface_regex=None) -> list:
        return dict(
            MetricsTable(
                self.device
            ).get(
                interface_name=interface_regex
            ) if interface_regex else MetricsTable(
                self.device
            ).get()
        )

    def get_environment(self):
        software = SoftwareTable(self.device).get()
        rengine = RoutingEngineTable(self.device).get()
        rengine_dict = {k: dict(v) for k, v in rengine.items()}
        uptime = rengine_dict['0']['uptime']
        temperatures = EnvironmentTable(self.device).get()
        return {
            **{'uptime': uptime},
            **{k: v for value in {k: dict(v) for k, v in software.items()}.values() for k, v in value.items()},
            **{'re_loads': rengine_dict},
            **{'Temp': {k: dict(v) for k, v in temperatures.items() if 'Temp' == dict(v)['class']}},
            **{'Fans': {k: dict(v) for k, v in temperatures.items() if 'Fans' == dict(v)['class']}},
            **{'Power': {k: dict(v) for k, v in temperatures.items() if 'Power' == dict(v)['class']}}
        }

    def get_igmp(self):
        igmp = dict(IGMPGroupTable(self.device).get())
        igmp = {
            key: dict(value) for key, value in igmp.items() if 'local' not in key
        }
        for value in igmp.values():
            if isinstance(value['mgm_addresses'], str):
                value['mgm_addresses'] = [value['mgm_addresses']]
        return igmp

    def lookup_ospf(self, ospf):
        if 'neighbor_id' in ospf.keys():
            ospf['neighbor_id'] = self.lookup(ospf['neighbor_id'])
        return ospf

    def manipulate_ospf(self, ospf, ospf_type: OSPFType = OSPFType.OSPF):
        result = {}
        for interface_name in ospf.keys():
            splitted_name = interface_name.split('.', 1)
            interface = splitted_name[0]
            try:
                unit = int(splitted_name[1])
                if interface not in result.keys():
                    result[interface] = {
                        ospf_type.value: []
                    }
                result[interface][ospf_type.value].append(
                    {
                        **{"unit": unit}, **self.lookup_ospf(
                            dict(
                                ospf.get(
                                    interface_name, {}
                                )
                            )
                        )
                    }
                )
            except IndexError as e:
                self.exception_counter.labels(
                    exception=type(e).__name__,
                    collector=type(self).__name__,
                    hostname=self.device.hostname
                ).inc()
        return result

    def get_ospf(self, interface_regex: str = None):
        return self.manipulate_ospf(
            dict(
                OspfNeighborTable(
                    self.device).get(
                    interface=interface_regex
                )
                if interface_regex else
                OspfNeighborTable(
                    self.device
                ).get()
            ),
            ospf_type=OSPFType.OSPF
        )

    def get_ospf3(self, interface_regex: str = None):
        return self.manipulate_ospf(
            dict(
                Ospf3NeighborTable(
                    self.device).get(
                    interface=interface_regex
                )
                if interface_regex else
                Ospf3NeighborTable(
                    self.device
                ).get()
            ),
            ospf_type=OSPFType.OSPF3
        )

    def get_optics(self, interface_regex=None):
        return dict(
            PhyPortDiagTable(
                self.device
            ).get(
                interface_name=interface_regex
            ) if interface_regex else
            PhyPortDiagTable(
                self.device
            ).get()
        )

    def is_connected(self):
        return self.device.connected

    def connect(self):
        self.device.open()

    def disconnect(self):
        if self.is_connected():
            self.device.close()
        return self.is_connected()

    def collect(self):
        try:
            if not self.lock.acquire(False):
                raise Exception("{} is locked.".format(self.device.hostname))
            self.connect()
            self.device.timeout = 60
            return 200, "OK", generate_latest(self.registry)
        except (Exception, ConnectAuthError, AuthenticationError, RpcTimeoutError) as exception:
            exception_name = type(exception).__name__
            self.exception_counter.labels(
                exception=exception_name, collector=type(self).__name__, hostname=self.device.hostname).inc()
            raise exception
        finally:
            # fix the memory consumption problem?
            self.disconnect()
            self.lock.release()
