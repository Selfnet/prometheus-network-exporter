"""Reply layouts seen on real Junos 21.4 EX4600 switches."""

import pytest

from .conftest import FIXTURES, labels_of, make_device, samples, scrape, value

SHAPES = FIXTURES / "junos-21.4-shapes"


@pytest.fixture
def found():
    device = make_device(
        SHAPES, types=["bgp", "bgp_details", "ddos", "fib", "pim", "system", "krt", "vxlan", "ospf", "ospf_details"]
    )
    result = samples(scrape(device))
    assert not device.schema.missing
    return result


def test_split_bgp_groups_are_summed(found):
    assert value(found, "pyez_junos_bgp_group_peers", group="iBGP-RR", type="Internal") == 22
    assert value(found, "pyez_junos_bgp_group_established_peers", group="iBGP-RR") == 15
    assert value(found, "pyez_junos_bgp_group_peers", group="iBGP-access") == 40


def test_ddos_labels_inside_statistics(found):
    assert (
        value(found, "pyez_junos_ddos_packets_total", group="ospf", packet_type="aggregate", counter="packet-dropped")
        == 12
    )
    assert value(found, "pyez_junos_ddos_packets_total", group="ospf", counter="policer-violation-count") == 1
    assert value(found, "pyez_junos_ddos_rate_pps", group="ospf", counter="packet-arrival-rate") == 47
    assert value(found, "pyez_junos_ddos_violations") == 0


def test_fib_skips_separators_and_keeps_bridge_domains(found):
    assert value(found, "pyez_junos_fib_routes", table="default.inet", type="user") == 3073
    assert value(found, "pyez_junos_fib_routes", table="default-switch.evpn-vxlan", bridge_domain="") == 2
    assert value(found, "pyez_junos_fib_routes", bridge_domain="bd100.evpn-vxlan") == 7


def test_pim_interface_name_inside_neighbor(found):
    assert value(found, "pyez_junos_pim_neighbors", interface="et-0/0/24.0") == 2
    assert value(found, "pyez_junos_pim_neighbor_up_seconds", neighbor="198.51.100.70") == 89059
    assert labels_of(found, "pyez_junos_pim_neighbor_up_seconds", neighbor="fe80::1")["interface"] == "et-0/0/24.0"


def test_ntp_query_timeout_is_reported_not_a_schema_gap(found):
    assert value(found, "pyez_junos_ntp_query_failed") == 1
    assert "pyez_junos_ntp_synced" not in found


def test_krt_state_nested_queue_counters(found):
    assert value(found, "pyez_junos_krt_state", field="krtq_operations_queued") == 3
    assert value(found, "pyez_junos_krt_state", field="krtq_kernel_rt_learnt") == 39
    assert value(found, "pyez_junos_krt_state", field="rtsock_time_until_next_scan") == 51
    assert value(found, "pyez_junos_krt_queue_entries", queue="normal_priority_add_queue") == 3


def test_vxlan_without_remote_vteps_is_zero(found):
    assert value(found, "pyez_junos_vxlan_remote_vteps") == 0
    assert "pyez_junos_vxlan_remote_vtep_vnis" not in found


def test_ospf_interface_with_two_addresses(found):
    assert value(found, "pyez_junos_ospf_interface_state", interface="lo0.0", address="192.0.2.1", state="DRother") == 1
    assert (
        value(found, "pyez_junos_ospf_interface_state", interface="lo0.0", address="192.0.2.254", state="DRother") == 1
    )
