"""Collector isolation, per module device objects and the per prefix route watch."""

import shutil

import pytest
from jnpr.junos.exception import RpcTimeoutError

from prometheus_network_exporter.collectors.junos.system import RoutingEngineCollector
from prometheus_network_exporter.handlers.device import ExporterHandler

from .conftest import ROUTING_OPTIONS, SYNTHETIC, labels_of, make_device, samples, scrape, value


def test_failing_collector_does_not_take_the_scrape_down(monkeypatch):
    def broken(self):
        yield from ()
        raise KeyError("schema changed")

    monkeypatch.setattr(RoutingEngineCollector, "collect", broken)
    device = make_device(SYNTHETIC, types=["routing_engine", "fpc"])
    found = samples(scrape(device))
    assert value(found, "pyez_junos_collector_failed", collector="route_engine") == 1
    assert value(found, "pyez_junos_fpc_cpu_ratio", slot="0", window="current") == 0.22
    assert value(found, "pyez_junos_collector_duration_seconds", collector="fpc") >= 0
    assert (
        device.exception_counter.labels(
            exception="KeyError", collector="JuniperNetworkDevice", hostname="switch.example.com"
        )._value.get()
        == 1
    )


def test_session_errors_still_abort_the_scrape(monkeypatch):
    def timeout(self):
        yield from ()
        raise RpcTimeoutError(None, "get-route-engine-information", 20)

    monkeypatch.setattr(RoutingEngineCollector, "collect", timeout)
    device = make_device(SYNTHETIC, types=["routing_engine", "fpc"])
    with pytest.raises(RpcTimeoutError):
        scrape(device)


def test_rpc_timeout_option():
    assert make_device(SYNTHETIC, types=[], options={"rpc_timeout": 15}).rpc_timeout == 15
    assert make_device(SYNTHETIC, types=[]).rpc_timeout == 60


def test_one_device_object_per_module():
    assert ExporterHandler.pool_key("a.example", "core_fast") != ExporterHandler.pool_key("a.example", "core_slow")


def test_route_watch_by_destination():
    options = dict(ROUTING_OPTIONS)
    device = make_device(SYNTHETIC, types=["routes", "route_watch"], options=options)
    text = scrape(device)
    types = [line.split()[2] for line in text.splitlines() if line.startswith("# TYPE")]
    assert len(types) == len(set(types)), "a metric family is exported by two collectors"
    found = samples(text)
    assert value(found, "pyez_junos_route_watch_present", table="inet.0", prefix="0.0.0.0/0") == 1
    assert value(found, "pyez_junos_route_watch_present", table="inet6.0", prefix="::/0") == 1
    assert value(found, "pyez_junos_route_watch_present", table="inet.0", prefix="203.0.113.0/25") == 0
    assert value(found, "pyez_junos_route_watch_nexthops", prefix="0.0.0.0/0") == 2
    assert value(found, "pyez_junos_route_watch_age_seconds", prefix="::/0") == 600
    info = labels_of(found, "pyez_junos_route_watch_info", prefix="0.0.0.0/0")
    assert info["via"] == "et-0/0/26.0,xe-0/2/0.0"
    # The table dump no longer exports watch metrics, so nothing is doubled.
    assert not device.schema.missing
    calls = device.device.rpc.calls
    assert "route_destination_inet.0_0.0.0.0_0" in calls


def test_route_watch_failed_lookup_is_unknown(tmp_path):
    device = make_device(tmp_path, types=["route_watch"], options={"watch": ["0.0.0.0/0"]})
    found = samples(scrape(device))
    assert "pyez_junos_route_watch_present" not in found
    assert value(found, "pyez_junos_rpc_failed", rpc="route_destination_inet.0_0.0.0.0_0") == 1


def test_route_watch_asks_every_table_of_the_family(tmp_path):
    shutil.copy(SYNTHETIC / "route_destination_inet.0_0.0.0.0_0.xml", tmp_path)
    (tmp_path / "route_destination_customer.inet.0_0.0.0.0_0.xml").write_text(
        "<rpc-reply><route-information><route-table><table-name>customer.inet.0</table-name>"
        "</route-table></route-information></rpc-reply>"
    )
    options = {"tables": ["inet.0", "customer.inet.0", "inet6.0"], "watch": ["0.0.0.0/0"]}
    device = make_device(tmp_path, types=["route_watch"], options=options)
    found = samples(scrape(device))
    assert value(found, "pyez_junos_route_watch_present", table="inet.0", prefix="0.0.0.0/0") == 1
    assert value(found, "pyez_junos_route_watch_present", table="customer.inet.0", prefix="0.0.0.0/0") == 0
    # An IPv4 prefix is looked up in every IPv4 table and never in inet6.0.
    assert device.device.rpc.calls == [
        "route_destination_inet.0_0.0.0.0_0",
        "route_destination_customer.inet.0_0.0.0.0_0",
    ]


def test_rpc_timeout_aborts_the_scrape(monkeypatch):
    device = make_device(SYNTHETIC, types=["routing_engine", "fpc"])
    original = device.device.rpc.__class__.__getattr__

    def getattr_with_timeout(self, name):
        if name == "get_route_engine_information":

            def call(**kwargs):
                raise RpcTimeoutError(None, name, 20)

            return call
        return original(self, name)

    monkeypatch.setattr(device.device.rpc.__class__, "__getattr__", getattr_with_timeout)
    with pytest.raises(RpcTimeoutError):
        scrape(device)
    assert "route_engine" in device.rpc_failed
    # The FPC RPC was never sent: one timeout, not one per RPC.
    assert "fpc" not in device.device.rpc.calls


def test_unrenderable_value_costs_only_that_family(monkeypatch):
    from prometheus_client.core import GaugeMetricFamily

    def broken(self):
        family = GaugeMetricFamily("pyez_junos_broken", "value is None")
        family.add_metric([], None)
        yield family

    monkeypatch.setattr(RoutingEngineCollector, "collect", broken)
    found = samples(scrape(make_device(SYNTHETIC, types=["routing_engine", "fpc"])))
    assert "pyez_junos_broken" not in found
    assert value(found, "pyez_junos_collector_failed", collector="route_engine") == 1
    assert value(found, "pyez_junos_fpc_cpu_ratio", slot="0", window="current") == 0.22


def test_failed_reverse_lookup_keeps_the_address(monkeypatch):
    import socket

    from prometheus_network_exporter.devices.basedevice import Device

    def fail(ip):
        raise socket.gaierror(8, "nodename nor servname provided")

    monkeypatch.setattr(socket, "gethostbyaddr", fail)
    device = Device("switch.example.com", None, types=[])
    assert device.lookup("fe80::1%irb.100") == "fe80::1%irb.100"


def test_unlock_skips_busy_devices(monkeypatch):
    import threading

    from prometheus_network_exporter import CONNECTION_POOL
    from prometheus_network_exporter.handlers import unlock

    class Fake:
        def __init__(self):
            self.lock = threading.Lock()
            self.closed = False

        def disconnect(self):
            self.closed = True

    idle, busy, other = Fake(), Fake(), Fake()
    busy.lock.acquire()
    monkeypatch.setattr(unlock, "UNLOCK_TIMEOUT_SECONDS", 0.01)
    CONNECTION_POOL.update({"a.example|fast": idle, "a.example|slow": busy, "b.example|fast": other})
    try:
        code, _, _ = unlock.unlock_device("a.example")
        assert code == 409
        assert idle.closed and not busy.closed and not other.closed
        assert "a.example|fast" not in CONNECTION_POOL
        assert "a.example|slow" in CONNECTION_POOL and "b.example|fast" in CONNECTION_POOL
        assert unlock.unlock_device("c.example")[0] == 404
    finally:
        busy.lock.release()
        for key in ("a.example|fast", "a.example|slow", "b.example|fast"):
            CONNECTION_POOL.pop(key, None)
