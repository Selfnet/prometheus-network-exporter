"""Load protection: one session slot per switch, kept probe sessions."""

import threading

import pytest

from prometheus_network_exporter.devices import junosdevice
from prometheus_network_exporter.devices.junosdevice import DeviceBusy

from .conftest import SYNTHETIC, make_device, samples


def collect(device):
    code, _, body = device.collect()
    assert code == 200
    return samples(body.decode("utf-8"))


@pytest.fixture(autouse=True)
def fresh_slots(monkeypatch):
    monkeypatch.setattr(junosdevice, "_SESSION_SLOTS", {})


def test_default_logs_in_and_out_per_scrape():
    device = make_device(SYNTHETIC, types=["probe"])
    device.device.connected = False
    collect(device)
    collect(device)
    assert (device.device.opened, device.device.closed) == (2, 2)


def test_kept_session_logs_in_once():
    device = make_device(SYNTHETIC, types=["probe"], options={"keep_session": True})
    device.device.connected = False
    first = collect(device)
    second = collect(device)
    assert (device.device.opened, device.device.closed) == (1, 0)
    assert first["pyez_junos_netconf_session_reused"][0][1] == 0
    assert second["pyez_junos_netconf_session_reused"][0][1] == 1
    assert "pyez_junos_netconf_connect_seconds" not in second


def test_kept_session_is_closed_after_a_failure(monkeypatch):
    device = make_device(SYNTHETIC, types=["probe"], options={"keep_session": True})
    device.device.connected = False
    collect(device)

    def boom(*args, **kwargs):
        raise junosdevice.TransportError("session gone")

    monkeypatch.setattr(junosdevice, "generate_latest", boom)
    with pytest.raises(junosdevice.TransportError):
        device.collect()
    assert device.device.connected is False


def test_second_module_waits_for_the_session_slot():
    fast = make_device(SYNTHETIC, types=["fpc"], options={"session_wait_seconds": 0})
    slot = junosdevice.session_slot(fast.hostname)
    slot.acquire()
    try:
        with pytest.raises(DeviceBusy):
            fast.collect()
        # Never connected while another module held the slot.
        assert fast.device.opened == 0
    finally:
        slot.release()
    collect(fast)


def test_probe_bypasses_the_slot():
    probe = make_device(SYNTHETIC, types=["probe"], options={"exclusive_session": False, "keep_session": True})
    slot = junosdevice.session_slot(probe.hostname)
    slot.acquire()
    try:
        collect(probe)
    finally:
        slot.release()


def test_slot_is_released_after_errors(monkeypatch):
    device = make_device(SYNTHETIC, types=["fpc"], options={"session_wait_seconds": 0})

    def boom(*args, **kwargs):
        raise junosdevice.TransportError("session gone")

    monkeypatch.setattr(junosdevice, "generate_latest", boom)
    with pytest.raises(junosdevice.TransportError):
        device.collect()
    assert junosdevice.session_slot(device.hostname).acquire(blocking=False)


def test_slots_are_per_switch():
    assert junosdevice.session_slot("a") is junosdevice.session_slot("a")
    assert junosdevice.session_slot("a") is not junosdevice.session_slot("b")
    assert isinstance(junosdevice.session_slot("a"), type(threading.Semaphore()))


def _timeout_on(device, rpc_name):
    from jnpr.junos.exception import RpcTimeoutError

    rpc = device.device.rpc
    original = type(rpc).__getattr__

    class TimingOut(type(rpc)):
        def __getattr__(self, name):
            if name == rpc_name:
                def call(**kwargs):
                    raise RpcTimeoutError(None, name, 10)
                return call
            return original(self, name)

    rpc.__class__ = TimingOut


def test_timeout_returns_status_instead_of_500():
    device = make_device(SYNTHETIC, types=["probe"], options={"keep_session": True, "exclusive_session": False})
    device.device.connected = False
    _timeout_on(device, "get_software_information")
    found = collect(device)
    assert found["pyez_junos_scrape_aborted"] == [({"reason": "RpcTimeoutError"}, 1.0)]
    assert ({"rpc": "probe"}, 1.0) in found["pyez_junos_rpc_failed"]
    assert "pyez_junos_probe_success" not in found
    # The half dead session is dropped and the lock is free again.
    assert device.device.connected is False
    assert device.lock.acquire(blocking=False)
    device.lock.release()


def test_failing_close_does_not_leak_the_lock(monkeypatch):
    device = make_device(SYNTHETIC, types=["fpc"])

    def close():
        raise RuntimeError("close-session timed out")

    monkeypatch.setattr(device.device, "close", close)
    collect(device)
    assert device.lock.acquire(blocking=False)
    device.lock.release()
    assert junosdevice.session_slot(device.hostname).acquire(blocking=False)
