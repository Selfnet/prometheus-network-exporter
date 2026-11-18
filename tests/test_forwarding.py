"""PFE, DDoS protection, hardware tables, KRT, rpd memory, FIB, ARP/ND."""

import pytest

from .conftest import CONTROL_PLANE_TYPES, SYNTHETIC, make_device, samples, scrape, value


@pytest.fixture
def found():
    return samples(scrape(make_device(SYNTHETIC, types=CONTROL_PLANE_TYPES)))


def test_pfe_traffic(found):
    name = "pyez_junos_pfe_statistics_total"
    assert value(found, name, section="pfe-traffic-statistics", counter="software-input-control-plane-drops") == 42
    assert value(found, name, section="pfe-traffic-statistics", counter="hardware-input-drops") == 1000
    assert value(found, name, section="pfe-hardware-discard-statistics", counter="nexthop-discard") == 17
    assert value(found, "pyez_junos_pfe_statistics_rate", section="pfe-traffic-statistics", counter="input-pps") == 12000


def test_pfe_exceptions_from_text(found):
    assert value(found, "pyez_junos_pfe_exceptions_total", type="discard_route") == 100
    assert value(found, "pyez_junos_pfe_exceptions_total", type="sw_error") == 5


def test_hardware_tables(found):
    assert value(found, "pyez_junos_pfe_hw_table_max_entries", unit="0", table="ipv4_lpm") == 12288
    assert value(found, "pyez_junos_pfe_hw_table_used_entries", unit="0", table="ipv6_lpm_gt_64") == 9
    assert value(found, "pyez_junos_pfe_hw_table_used_entries", unit="0", table="ipv6_lpm_lt_64") == 79


def test_ddos(found):
    assert value(found, "pyez_junos_ddos_packets_total", group="OSPF", packet_type="aggregate", counter="packet-dropped") == 5
    assert value(found, "pyez_junos_ddos_rate_pps", group="ARP", packet_type="aggregate", counter="packet-arrival-rate") == 12
    assert value(found, "pyez_junos_ddos_violations") == 1
    assert value(found, "pyez_junos_ddos_violation_active", group="OSPF", packet_type="aggregate") == 1


def test_krt_from_text(found):
    assert value(found, "pyez_junos_krt_queue_entries", queue="normal_priority_add_queue") == 17
    assert value(found, "pyez_junos_krt_queue_entries", queue="routing_table_add_queue") == 0
    assert value(found, "pyez_junos_krt_state", field="number_of_operations_queued") == 17
    assert value(found, "pyez_junos_krt_state", field="routes_learned_from_kernel") == 12


def test_krt_queue_from_xml(tmp_path):
    (tmp_path / "krt_queue.xml").write_text(
        "<rpc-reply><krt-queue-information>"
        "<krt-queue><krtq-type>Normal-priority add queue</krtq-type><krtq-queue-length>3</krtq-queue-length></krt-queue>"
        "</krt-queue-information></rpc-reply>"
    )
    (tmp_path / "krt_state.xml").write_text(
        "<rpc-reply><krt-state-information><krt-state>"
        "<krtq-operations-queued>3</krtq-operations-queued></krt-state></krt-state-information></rpc-reply>"
    )
    device = make_device(tmp_path, types=["krt"])
    result = samples(scrape(device))
    assert value(result, "pyez_junos_krt_queue_entries", queue="normal_priority_add_queue") == 3
    assert value(result, "pyez_junos_krt_state", field="krtq_operations_queued") == 3
    assert not device.schema.missing


def test_rpd_memory(found):
    assert value(found, "pyez_junos_rpd_task_memory", field="task_memory_in_use_size") == 412345
    assert value(found, "pyez_junos_rpd_task_memory", field="task_memory_in_use_avail") == 21


def test_fib(found):
    assert value(found, "pyez_junos_fib_routes", table="default.inet", type="user") == 145
    assert value(found, "pyez_junos_fib_routes", table="default.inet6", type="user") == 98


def test_neighbor_tables(found):
    assert value(found, "pyez_junos_arp_entries") == 2
    assert value(found, "pyez_junos_nd_entries", state="stale") == 2
    assert value(found, "pyez_junos_nd_entries", state="reachable") == 1
    assert value(found, "pyez_junos_nd_entries", state="incomplete") == 0


def test_unparsable_text_is_reported_not_zero(tmp_path):
    (tmp_path / "pfe_hw_routes.xml").write_text("<rpc-reply><output>error: command is not valid</output></rpc-reply>")
    device = make_device(tmp_path, types=["pfe_hw_tables"])
    result = samples(scrape(device))
    assert "pyez_junos_pfe_hw_table_used_entries" not in result
    assert value(result, "pyez_junos_xml_missing_fields", collector="pfe_hw_routes", field="output:table-rows") == 1
