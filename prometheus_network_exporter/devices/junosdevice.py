"""
Juniper device: opens a NETCONF session per scrape and runs the collectors.
"""

from __future__ import annotations

import logging
import threading
import time

from jnpr.junos import Device
from jnpr.junos.exception import (
    ConnectAuthError,
    ConnectClosedError,
    ConnectError,
    RpcError,
    RpcTimeoutError,
)
from ncclient.operations.errors import TimeoutExpiredError
from ncclient.transport.errors import AuthenticationError, TransportError
from prometheus_client import CollectorRegistry, generate_latest

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
from prometheus_network_exporter.collectors.junos.optics import StandaloneOpticsCollector
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
from prometheus_network_exporter.collectors.junos.links import (
    DEFAULT_EXTENSIVE_DESCRIPTION,
    DEFAULT_EXTENSIVE_INTERFACES,
    DEFAULT_LOGICAL_INTERFACES,
    InterfaceErrorCollector,
    LACPCollector,
    LLDPCollector,
    LogicalInterfaceCollector,
    VxlanCollector,
)
from prometheus_network_exporter.collectors.junos.pfe import (
    DDoSCollector,
    HardwareTableCollector,
    PFEExceptionCollector,
    PFEStatisticsCollector,
)
from prometheus_network_exporter.collectors.junos.route import (
    RouteSummaryCollector,
    RouteTableCollector,
    RouteWatchCollector,
)
from prometheus_network_exporter.collectors.junos.routing_extra import (
    ForwardingTableCollector,
    KRTCollector,
    L2CircuitCollector,
    LDPCollector,
    NeighborTableCollector,
    PIMCollector,
    TaskMemoryCollector,
)
from prometheus_network_exporter.collectors.junos.system import (
    DEFAULT_PROCESS_TOP,
    DEFAULT_PROCESSES,
    DEFAULT_STORAGE_MOUNTS,
    AlarmCollector,
    CoreDumpCollector,
    FPCCollector,
    NTPCollector,
    ProbeCollector,
    ProcessCollector,
    RoutingEngineCollector,
    StorageCollector,
    UptimeCollector,
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
DEFAULT_RPC_TIMEOUT = 60
DEFAULT_SESSION_WAIT_SECONDS = 30

# One "heavy" NETCONF session per switch at a time, across all modules of
# this exporter process. Without it a fast, a slow and the legacy module
# would open up to three sessions on the same routing engine at once.
_SESSION_SLOTS = {}
_SESSION_SLOTS_LOCK = threading.Lock()


def session_slot(hostname: str) -> threading.Semaphore:
    with _SESSION_SLOTS_LOCK:
        return _SESSION_SLOTS.setdefault(hostname, threading.Semaphore(1))


class DeviceBusy(Exception):
    """Another module of this exporter holds the session slot of the device."""


# Errors after which the NETCONF session is unusable or the device does not
# answer. They abort the scrape, so a stalled device costs one timeout instead
# of one per RPC; every other collector error only costs that collector's
# metrics. ncclient and PyEZ wrap socket errors into these.
FATAL_ERRORS = (
    RpcTimeoutError,
    TimeoutExpiredError,
    ConnectError,
    ConnectClosedError,
    TransportError,
)

# Metric types that are served by one collector class each, with the
# constructor taking only the device.
SIMPLE_COLLECTORS = {
    "probe": (ProbeCollector,),
    "routing_engine": (RoutingEngineCollector,),
    "fpc": (FPCCollector,),
    "alarms": (AlarmCollector,),
    "core_dumps": (CoreDumpCollector,),
    "system": (UptimeCollector, NTPCollector),
    "pfe": (PFEStatisticsCollector,),
    "pfe_exceptions": (PFEExceptionCollector,),
    "pfe_hw_tables": (HardwareTableCollector,),
    "ddos": (DDoSCollector,),
    "krt": (KRTCollector,),
    "rpd_memory": (TaskMemoryCollector,),
    "fib": (ForwardingTableCollector,),
    "ldp": (LDPCollector,),
    "l2circuit": (L2CircuitCollector,),
    "pim": (PIMCollector,),
    "neighbor_tables": (NeighborTableCollector,),
    "lacp": (LACPCollector,),
    "lldp": (LLDPCollector,),
    "vxlan": (VxlanCollector,),
}


def collector_label(collector) -> str:
    """Stable name of a collector for the duration and failure metrics."""
    reader = getattr(collector, "reader", None)
    if reader is not None:
        return reader.collector
    name = type(collector).__name__
    protocol = getattr(collector, "protocol", None)
    return f"{name}:{protocol}" if protocol else name


def flush_legacy(collector) -> None:
    """Reset the metric families a legacy YAML collector keeps between scrapes.

    Those collectors add samples to long lived families and flush them after
    yielding. If one fails half way the samples would otherwise be reported
    twice on the next scrape, and Prometheus rejects a scrape with duplicate
    series.
    """
    for metric in getattr(collector, "prometheus_metrics", {}).values():
        metric.flush()
    for child in getattr(collector, "collectors", []):
        flush_legacy(child)


class IsolatedCollector:
    """Times a collector and keeps its errors from failing the whole scrape.

    A parsing error in one collector used to abort the scrape, so every
    metric of the device was lost. Now only that collector's remaining
    metrics are lost and ``pyez_junos_collector_failed`` names it. Errors
    that mean the session is gone still abort the scrape.
    """

    def __init__(self, collector, device):
        self.collector = collector
        self.device = device
        self.label = collector_label(collector)

    def _valid(self, family) -> bool:
        """False when a sample value cannot be rendered.

        generate_latest converts values only while writing the output, after
        this wrapper returned; a None there would fail the whole scrape.
        """
        for sample in family.samples:
            try:
                float(sample.value)
            except (TypeError, ValueError):
                LOGGER.warning(
                    "%s :: collector %s: dropped %s, value %r",
                    self.device.hostname, self.label, family.name, sample.value,
                )
                self.device.collector_failed.add(self.label)
                return False
        return True

    def collect(self):
        started = time.monotonic()
        try:
            for family in self.collector.collect():
                if self._valid(family):
                    yield family
        except FATAL_ERRORS:
            raise
        except Exception as exception:  # noqa: B902 - isolation is the point
            LOGGER.warning(
                "%s :: collector %s failed: %r", self.device.hostname, self.label, exception
            )
            self.device.collector_failed.add(self.label)
            self.device._count_exception(exception)
        finally:
            # Idempotent; also covers a fatal error half way through a legacy
            # collector, whose samples would otherwise reappear next scrape.
            flush_legacy(self.collector)
            durations = self.device.collector_durations
            durations[self.label] = durations.get(self.label, 0.0) + time.monotonic() - started


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
        self.collector_failed = set()
        self.collector_durations = {}
        self.connect_duration = None
        self.session_reused = False
        self.aborted = None
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

    @property
    def rpc_timeout(self) -> int:
        return int(self.options.get("rpc_timeout", DEFAULT_RPC_TIMEOUT))

    @property
    def keep_session(self) -> bool:
        """Reuse the NETCONF session between scrapes instead of logging in each time.

        Meant for the probe module: a login per 15s scrape means an SSH key
        exchange and a new mgd process on the routing engine every time.
        """
        return bool(self.options.get("keep_session", False))

    @property
    def exclusive_session(self) -> bool:
        """Wait for the per switch session slot before connecting (default)."""
        return bool(self.options.get("exclusive_session", True))

    @property
    def session_wait_seconds(self) -> float:
        return float(self.options.get("session_wait_seconds", DEFAULT_SESSION_WAIT_SECONDS))

    def _register(self, collector):
        self.registry.register(IsolatedCollector(collector, self))

    def register_collectors(self, types: list):
        for type_name, classes in SIMPLE_COLLECTORS.items():
            if type_name in types:
                for collector_class in classes:
                    self._register(collector_class(self))
        if "processes" in types:
            self._register(
                ProcessCollector(
                    self,
                    processes=self.options.get("processes", DEFAULT_PROCESSES),
                    top=self.options.get("process_top", DEFAULT_PROCESS_TOP),
                )
            )
        if "system" in types:
            self._register(
                StorageCollector(self, mounts=self.options.get("storage_mounts", DEFAULT_STORAGE_MOUNTS))
            )
        if "interface_errors" in types:
            self._register(
                InterfaceErrorCollector(
                    self,
                    interfaces=self.options.get("extensive_interfaces", DEFAULT_EXTENSIVE_INTERFACES),
                    description=self.options.get("extensive_description", DEFAULT_EXTENSIVE_DESCRIPTION),
                )
            )
        if "logical_interfaces" in types:
            self._register(
                LogicalInterfaceCollector(
                    self, interfaces=self.options.get("logical_interfaces", DEFAULT_LOGICAL_INTERFACES)
                )
            )
        if "route_watch" in types:
            self._register(RouteWatchCollector(self, watch=self.watch_prefixes, tables=self.route_tables))
        self._register_legacy_and_routing(types)
        # Last on purpose: it reports what the collectors above recorded.
        self.registry.register(StatusCollector(self))
        # Served instead of the full registry when the scrape was aborted.
        self.status_registry = CollectorRegistry()
        self.status_registry.register(StatusCollector(self))

    def _register_legacy_and_routing(self, types: list):
        ospf = True
        optics = True
        if "ospf" not in types:
            ospf = False
        if "optics" not in types:
            optics = False
        if "interface" in types and "interface_specifics" not in types:
            self._register(InterfaceCollector(self, ospf=ospf, optics=optics))
        if "interface_specifics" in types and "interface" not in types:
            self._register(
                InterfaceCollector(self, access=True, ospf=ospf, optics=optics)
            )
        if optics and "interface" not in types and "interface_specifics" not in types:
            # optics on its own, e.g. in a slow module next to a fast interface job
            self._register(StandaloneOpticsCollector(self))
        if "environment" in types:
            self._register(EnvironmentCollector(self))
        if "bgp" in types:
            self._register(BGPCollector(self))
            self._register(BGPNeighborCollector(self))
            self._register(BGPOverviewCollector(self))
        if "igmp" in types:
            self._register(IGMPCollector(self))
        if "ospf" in types:
            for protocol in OSPF_PROTOCOLS:
                self._register(OSPFStatisticsCollector(self, protocol=protocol))
                self._register(OSPFNeighborCollector(self, protocol))
                self._register(OSPFInterfaceCollector(self, protocol))
                self._register(OSPFOverviewCollector(self, protocol))
                self._register(OSPFDatabaseCollector(self, protocol))
                self._register(
                    OSPFRouteCollector(self, protocol, watch=self.watch_prefixes)
                )
        if "routes" in types:
            self._register(RouteSummaryCollector(self))
            self._register(
                RouteTableCollector(
                    self,
                    tables=self.route_tables,
                    # route_watch looks the prefixes up one by one instead.
                    watch=[] if "route_watch" in types else self.watch_prefixes,
                    young_seconds=self.young_route_seconds,
                )
            )
        if "bfd" in types:
            self._register(BFDCollector(self))

    # ------------------------------------------------------------------
    # RPC access for the lxml based collectors
    # ------------------------------------------------------------------
    def begin_scrape(self):
        self._rpc_cache.clear()
        self.rpc_failed.clear()
        self.rpc_durations.clear()
        self.collector_failed.clear()
        self.collector_durations.clear()
        self.connect_duration = None
        self.aborted = None
        self.schema.reset()

    def end_scrape(self):
        """Drop the cached replies; a route table dump is not worth keeping."""
        self._rpc_cache.clear()

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
        except RpcTimeoutError:
            # RpcTimeoutError is an RpcError, but the device did not answer
            # at all: abort the scrape instead of waiting for every RPC.
            self.rpc_failed.add(name)
            self.rpc_durations[name] = time.monotonic() - started
            raise
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

    def disconnect(self, force: bool = False):
        """Close the session; never raises.

        After a timed out RPC the device may not answer the polite
        close-session either, so ``force`` drops the transport right away.
        An exception here must not keep the scrape lock taken.
        """
        try:
            if self.is_connected():
                if force:
                    self._drop_transport()
                else:
                    self.device.close()
        except Exception as exception:  # noqa: B902 - cleanup must not raise
            LOGGER.warning("%s :: closing the session failed: %r", self.hostname, exception)
            self._count_exception(exception)
            self._drop_transport()
        return self._connected_safe()

    def _connected_safe(self) -> bool:
        try:
            return bool(self.is_connected())
        except Exception:  # noqa: B902
            return False

    def _drop_transport(self) -> None:
        """Close the SSH transport without a NETCONF round trip."""
        try:
            conn = getattr(self.device, "_conn", None)
            session = getattr(conn, "_session", None)
            if session is not None:
                session.close()
        except Exception as exception:  # noqa: B902
            LOGGER.warning("%s :: dropping the transport failed: %r", self.hostname, exception)
        try:
            self.device.connected = False
        except Exception:  # noqa: B902
            pass

    def collect(self):
        # The lock serialises scrapes of one device. It must only be released,
        # and the session only closed, by the thread that acquired it;
        # otherwise a second scrape request would tear down the running one.
        if not self.lock.acquire(False):
            locked = Exception("{} is locked.".format(self.device.hostname))
            self._count_exception(locked)
            raise locked
        slot = session_slot(self.hostname) if self.exclusive_session else None
        has_slot = False
        healthy = False
        try:
            if slot is not None:
                has_slot = slot.acquire(timeout=self.session_wait_seconds)
                if not has_slot:
                    raise DeviceBusy(
                        "{} is busy with another module for {}s".format(
                            self.hostname, self.session_wait_seconds
                        )
                    )
            self.begin_scrape()
            if self.keep_session and self.is_connected():
                self.session_reused = True
            else:
                self.session_reused = False
                started = time.monotonic()
                self.connect()
                self.connect_duration = time.monotonic() - started
            self.device.timeout = self.rpc_timeout
            try:
                body = generate_latest(self.registry)
                healthy = True
            except FATAL_ERRORS as exception:
                # The device stopped answering mid scrape. Report what is
                # known instead of a bare HTTP 500: which RPC hung and for how
                # long is exactly what a control plane stall needs.
                self._count_exception(exception)
                self.aborted = type(exception).__name__
                body = generate_latest(self.status_registry)
            return 200, "OK", body
        except (
            Exception,
            ConnectAuthError,
            AuthenticationError,
            RpcTimeoutError,
        ) as exception:
            self._count_exception(exception)
            raise exception
        finally:
            try:
                self.end_scrape()
                # A kept session is closed after any failure, so the next
                # scrape starts with a fresh one instead of a half dead one.
                if not (self.keep_session and healthy):
                    self.disconnect(force=not healthy)
            finally:
                if has_slot:
                    slot.release()
                self.lock.release()
