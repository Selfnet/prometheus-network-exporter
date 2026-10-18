"""
Juniper device: opens a NETCONF session per scrape and runs the collectors.
"""

from __future__ import annotations

import logging
import time

from jnpr.junos import Device
from jnpr.junos.exception import RpcError, ConnectAuthError, RpcTimeoutError
from ncclient.transport.errors import AuthenticationError
from prometheus_client import generate_latest

from prometheus_network_exporter.collectors.junos.bfd import BFDCollector
from prometheus_network_exporter.collectors.junos.bgp import BGPCollector
from prometheus_network_exporter.collectors.junos.bgp_neighbor import (
    BGPNeighborCollector,
)
from prometheus_network_exporter.collectors.junos.bgp_overview import (
    BGPOverviewCollector,
)
from prometheus_network_exporter.collectors.junos.environment import (
    EnvironmentCollector,
)
from prometheus_network_exporter.collectors.junos.igmp import IGMPCollector
from prometheus_network_exporter.collectors.junos.interface import InterfaceCollector
from prometheus_network_exporter.collectors.junos.ospf_database import (
    OSPFDatabaseCollector,
)
from prometheus_network_exporter.collectors.junos.ospf_interface import (
    OSPFInterfaceCollector,
)
from prometheus_network_exporter.collectors.junos.ospf_neighbor import (
    OSPFNeighborCollector,
)
from prometheus_network_exporter.collectors.junos.ospf_overview import (
    OSPFOverviewCollector,
)
from prometheus_network_exporter.collectors.junos.ospf_route import (
    OSPFRouteCollector,
)
from prometheus_network_exporter.collectors.junos.ospf_statistics import (
    OSPFStatisticsCollector,
)
from prometheus_network_exporter.collectors.junos.route import (
    RouteSummaryCollector,
    RouteTableCollector,
)
from prometheus_network_exporter.collectors.junos.rpcs import (
    OSPF_PROTOCOLS,
    fixture_name,
)
from prometheus_network_exporter.collectors.junos.status import StatusCollector
from prometheus_network_exporter.collectors.junos.xmlutil import SchemaWatch
from prometheus_network_exporter.devices import basedevice
from prometheus_network_exporter.views.junos.bgp import BGPNeighborTable
from prometheus_network_exporter.views.junos.environment import (
    EnvironmentTable,
    RoutingEngineTable,
    SoftwareTable,
)
from prometheus_network_exporter.views.junos.igmp import IGMPGroupTable
from prometheus_network_exporter.views.junos.interface_metrics import MetricsTable
from prometheus_network_exporter.views.junos.optic import PhyPortDiagTable
from prometheus_network_exporter.views.junos.ospf import (
    Ospf3NeighborTable,
    OspfNeighborTable,
)

from ..config.junos import OSPFType

LOGGER = logging.getLogger("network_exporter")

DEFAULT_ROUTE_TABLES = ("inet.0", "inet6.0")
DEFAULT_YOUNG_ROUTE_SECONDS = 300


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
            fact_style="old",
        )
        # Per scrape bookkeeping, reset by begin_scrape().
        self.schema = SchemaWatch()
        self._rpc_cache = {}
        self.rpc_failed = set()
        self.rpc_durations = {}
        super(JuniperNetworkDevice, self).__init__(hostname, device, **kwargs)
        self.register_collectors(self.types)

    # ------------------------------------------------------------------
    # configuration helpers
    # ------------------------------------------------------------------
    @property
    def route_tables(self) -> list:
        return list(self.options.get("tables", DEFAULT_ROUTE_TABLES))

    @property
    def watch_prefixes(self) -> list:
        return list(self.options.get("watch", []))

    @property
    def young_route_seconds(self) -> float:
        return float(self.options.get("young_route_seconds", DEFAULT_YOUNG_ROUTE_SECONDS))

    def register_collectors(self, types: list):
        ospf = True
        optics = True
        if "ospf" not in types:
            ospf = False
        if "optics" not in types:
            optics = False
        if "interface" in types and "interface_specifics" not in types:
            self.registry.register(InterfaceCollector(self, ospf=ospf, optics=optics))
        if "interface_specifics" in types and "interface" not in types:
            self.registry.register(
                InterfaceCollector(self, access=True, ospf=ospf, optics=optics)
            )
        if "environment" in types:
            self.registry.register(EnvironmentCollector(self))
        if "bgp" in types:
            self.registry.register(BGPCollector(self))
            self.registry.register(BGPNeighborCollector(self))
            self.registry.register(BGPOverviewCollector(self))
        if "igmp" in types:
            self.registry.register(IGMPCollector(self))
        if "ospf" in types:
            for protocol in OSPF_PROTOCOLS:
                self.registry.register(OSPFStatisticsCollector(self, protocol=protocol))
                self.registry.register(OSPFNeighborCollector(self, protocol))
                self.registry.register(OSPFInterfaceCollector(self, protocol))
                self.registry.register(OSPFOverviewCollector(self, protocol))
                self.registry.register(OSPFDatabaseCollector(self, protocol))
                self.registry.register(
                    OSPFRouteCollector(self, protocol, watch=self.watch_prefixes)
                )
        if "routes" in types:
            self.registry.register(RouteSummaryCollector(self))
            self.registry.register(
                RouteTableCollector(
                    self,
                    tables=self.route_tables,
                    watch=self.watch_prefixes,
                    young_seconds=self.young_route_seconds,
                )
            )
        if "bfd" in types:
            self.registry.register(BFDCollector(self))
        # Last on purpose: it reports what the collectors above recorded.
        self.registry.register(StatusCollector(self))

    # ------------------------------------------------------------------
    # RPC access for the lxml based collectors
    # ------------------------------------------------------------------
    def begin_scrape(self):
        self._rpc_cache.clear()
        self.rpc_failed.clear()
        self.rpc_durations.clear()
        self.schema.reset()

    def rpc_reply(self, rpc: str, **args):
        """Run one RPC and return the reply element, None when Junos rejects it.

        Replies are cached for the current scrape so that collectors sharing
        an RPC, such as the BGP neighbour and overview collectors, cost one
        round trip.
        """
        key = (rpc, tuple(sorted(args.items())))
        if key in self._rpc_cache:
            return self._rpc_cache[key]
        name = fixture_name(rpc, args)
        started = time.monotonic()
        try:
            reply = getattr(self.device.rpc, rpc)(**args)
        except RpcError as error:
            LOGGER.info("%s :: %s failed: %s", self.hostname, name, error)
            self.rpc_failed.add(name)
            reply = None
        self.rpc_durations[name] = time.monotonic() - started
        self._rpc_cache[key] = reply
        return reply

    def _count_exception(self, exception):
        if self.exception_counter is None:
            return
        self.exception_counter.labels(
            exception=type(exception).__name__,
            collector=type(self).__name__,
            hostname=self.device.hostname,
        ).inc()

    # ------------------------------------------------------------------
    # legacy PyEZ table access
    # ------------------------------------------------------------------
    def get_ospf_statistics(self):
        reply = self.rpc_reply("get_ospf_statistics_information")
        return None if reply is None else reply.find(".//{*}ospf-statistics")

    def get_ospf3_statistics(self):
        reply = self.rpc_reply("get_ospf3_statistics_information")
        return None if reply is None else reply.find(".//{*}ospf-statistics")

    def get_bgp(self):
        try:
            bgp = dict(BGPNeighborTable(self.device).get())
        except RpcError:
            return {}
        bgp = {k: dict(v) for k, v in bgp.items()}
        for information in bgp.values():
            information["peername"] = self.lookup(information["peeraddr"])
        return bgp

    def get_interfaces(self, interface_regex=None) -> dict:
        return dict(
            MetricsTable(self.device).get(interface_name=interface_regex)
            if interface_regex
            else MetricsTable(self.device).get()
        )

    def get_environment(self):
        software = SoftwareTable(self.device).get()
        rengine = RoutingEngineTable(self.device).get()
        rengine_dict = {
            available_key: dict(v)
            for k, v in rengine.items()
            for available_key in k
            if available_key is not None
        }
        temperatures = EnvironmentTable(self.device).get()
        return {
            **(
                {
                    k: v
                    for value in {k: dict(v) for k, v in software.items()}.values()
                    for k, v in value.items()
                    if v is not None
                }
                if software
                else {}
            ),
            **{"re_loads": rengine_dict},
            **{
                "Temp": {
                    k: dict(v)
                    for k, v in temperatures.items()
                    if "Temp" == dict(v)["class"]
                }
            },
            **{
                "Fans": {
                    k: dict(v)
                    for k, v in temperatures.items()
                    if "Fans" == dict(v)["class"]
                }
            },
            **{
                "Power": {
                    k: dict(v)
                    for k, v in temperatures.items()
                    if "Power" == dict(v)["class"]
                }
            },
        }

    def get_igmp(self):
        igmp = dict(IGMPGroupTable(self.device).get())
        igmp = {key: dict(value) for key, value in igmp.items() if "local" not in key}
        for value in igmp.values():
            if isinstance(value["mgm_addresses"], str):
                value["mgm_addresses"] = [value["mgm_addresses"]]
        return igmp

    def lookup_ospf(self, ospf):
        if "neighbor_id" in ospf.keys():
            ospf["neighbor_id"] = self.lookup(ospf["neighbor_id"])
        return ospf

    def manipulate_ospf(self, ospf, ospf_type: OSPFType = OSPFType.OSPF):
        """Group neighbours by physical interface.

        The tables are keyed by (interface-name, neighbor-id) so that several
        neighbours on one broadcast segment do not overwrite each other.
        """
        result = {}
        for key, values in ospf.items():
            interface_name = key[0] if isinstance(key, tuple) else key
            if interface_name is None:
                continue
            splitted_name = interface_name.split(".", 1)
            interface = splitted_name[0]
            try:
                unit = int(splitted_name[1])
            except (IndexError, ValueError) as e:
                self._count_exception(e)
                continue
            result.setdefault(interface, {ospf_type.value: []})
            result[interface][ospf_type.value].append(
                {**{"unit": unit}, **self.lookup_ospf(dict(values))}
            )
        return result

    def get_ospf(self, interface_regex: str = None):
        return self.manipulate_ospf(
            dict(
                OspfNeighborTable(self.device).get(interface=interface_regex)
                if interface_regex
                else OspfNeighborTable(self.device).get()
            ),
            ospf_type=OSPFType.OSPF,
        )

    def get_ospf3(self, interface_regex: str = None):
        return self.manipulate_ospf(
            dict(
                Ospf3NeighborTable(self.device).get(interface=interface_regex)
                if interface_regex
                else Ospf3NeighborTable(self.device).get()
            ),
            ospf_type=OSPFType.OSPF3,
        )

    def get_optics(self, interface_regex=None):
        return dict(
            PhyPortDiagTable(self.device).get(interface_name=interface_regex)
            if interface_regex
            else PhyPortDiagTable(self.device).get()
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
            self.begin_scrape()
            self.connect()
            self.device.timeout = 60
            return 200, "OK", generate_latest(self.registry)
        except (
            Exception,
            ConnectAuthError,
            AuthenticationError,
            RpcTimeoutError,
        ) as exception:
            self._count_exception(exception)
            raise exception
        finally:
            # fix the memory consumption problem?
            self.disconnect()
            self.lock.release()
