"""What a scrape costs: legacy types stay cheap, rejected RPCs are not repeated, names are cached."""

from prometheus_network_exporter.devices.basedevice import Device

from .conftest import SYNTHETIC, make_device, samples, scrape, value


def test_bgp_and_ospf_types_stay_as_cheap_as_1_2_5():
    # The legacy interface table asks for statistics detail of the port
    # pattern; the fixture carries the name the fake derives from that call.
    device = make_device(SYNTHETIC, types=["ospf", "optics", "interface", "bgp"])
    found = samples(scrape(device))
    assert value(found, "pyez_junos_bgp_is_up_status", neighbor="192.0.2.102") == 1
    assert value(found, "pyez_junos_interface_ospf_neighbor_state", interface="ae0") == 1
    assert "pyez_junos_bgp_peer_state" not in found
    assert "pyez_junos_ospf_neighbor_state" not in found
    assert "pyez_junos_ospf_database_lsas" not in found
    # Exactly the RPCs of 1.2.5 for these types: interfaces, optics, the two
    # neighbour tables and the BGP summary. No LSDB, no show bgp neighbor.
    assert set(device.device.rpc.calls) == {
        "logical_interfaces_afgxe_et",
        "optics",
        "ospf_neighbor",
        "ospf3_neighbor",
        "bgp_summary",
    }


def test_details_types_carry_the_expensive_collectors():
    found = samples(scrape(make_device(SYNTHETIC, types=["bgp_details", "ospf_details"])))
    assert value(found, "pyez_junos_bgp_peer_state", peer="192.0.2.102", state="Established") == 1
    assert value(found, "pyez_junos_ospf_database_lsas", area="0.0.0.0", lsa_type="Router") >= 1
    assert "pyez_junos_bgp_is_up_status" not in found


def test_rejected_rpc_is_not_asked_again(tmp_path):
    for name in ("ospf_neighbor", "ospf_interface", "ospf_overview", "ospf_database", "ospf_route", "ospf_statistics"):
        (tmp_path / f"{name}.xml").write_bytes((SYNTHETIC / f"{name}.xml").read_bytes())
    device = make_device(tmp_path, types=["ospf_details"])
    scrape(device)
    found = samples(scrape(device))
    # OSPFv3 is rejected once per RPC, then remembered; the metric still says so.
    assert device.device.rpc.calls.count("ospf3_overview") == 1
    assert device.device.rpc.calls.count("ospf_overview") == 2
    assert value(found, "pyez_junos_rpc_failed", rpc="ospf3_overview") == 1
    assert value(found, "pyez_junos_ospf_full_spf_runs_total", topology="default") == 1234


def test_rejected_rpc_is_retried_after_the_window(tmp_path):
    device = make_device(tmp_path, types=["ospf_details"], options={"rpc_retry_seconds": 0})
    scrape(device)
    scrape(device)
    assert device.device.rpc.calls.count("ospf_overview") == 2


def test_reverse_lookups_are_cached_per_device(monkeypatch):
    calls = []

    def fake_resolve(ip):
        calls.append(ip)
        return f"name-of-{ip}"

    # Patch the device's resolver, not socket: PyEZ calls getfqdn() itself.
    monkeypatch.setattr(Device, "_resolve", staticmethod(fake_resolve))
    device = make_device(SYNTHETIC, types=["bgp", "bgp_details", "ospf", "ospf_details"])
    del device.lookup  # conftest stubs it; use the real cache here
    first = samples(scrape(device))
    resolved_once = len(calls)
    samples(scrape(device))
    assert len(calls) == resolved_once, "a second scrape must not resolve again"
    assert resolved_once == len(set(calls)), "every address is resolved once, even when two collectors need it"
    assert device.cache_info["entries"] == resolved_once
    assert value(first, "pyez_junos_bgp_is_up_status", neighbor="192.0.2.102") == 1
