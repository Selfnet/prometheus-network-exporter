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
    assert (
        value(found, "pyez_junos_pfe_statistics_rate", section="pfe-traffic-statistics", counter="input-pps") == 12000
    )


def test_pfe_exceptions_from_text(found):
    assert value(found, "pyez_junos_pfe_exceptions_total", type="discard_route") == 100
    assert value(found, "pyez_junos_pfe_exceptions_total", type="sw_error") == 5


def test_hardware_tables(found):
    assert value(found, "pyez_junos_pfe_hw_table_max_entries", unit="0", table="ipv4_lpm") == 12288
    assert value(found, "pyez_junos_pfe_hw_table_used_entries", unit="0", table="ipv6_lpm_gt_64") == 9
    assert value(found, "pyez_junos_pfe_hw_table_used_entries", unit="0", table="ipv6_lpm_lt_64") == 79


def test_ddos(found):
    assert (
        value(found, "pyez_junos_ddos_packets_total", group="OSPF", packet_type="aggregate", counter="packet-dropped")
        == 5
    )
    assert (
        value(found, "pyez_junos_ddos_rate_pps", group="ARP", packet_type="aggregate", counter="packet-arrival-rate")
        == 12
    )
    assert value(found, "pyez_junos_ddos_violations") == 1
    assert value(found, "pyez_junos_ddos_violation_active", group="OSPF", packet_type="aggregate") == 1


def test_ddos_reports_missing_protocol_labels(tmp_path):
    (tmp_path / "ddos_statistics.xml").write_text(
        "<ddos-protocols-information><ddos-protocol><ddos-system-statistics>"
        "<packet-dropped>5</packet-dropped></ddos-system-statistics></ddos-protocol></ddos-protocols-information>"
    )
    found = samples(scrape(make_device(tmp_path, types=["ddos"])))
    assert value(found, "pyez_junos_ddos_packets_total", group="", packet_type="", counter="packet-dropped") == 5
    for field in ("group-name", "packet-type"):
        assert value(found, "pyez_junos_xml_missing_fields", collector="ddos", field=field) == 1


@pytest.mark.parametrize(
    "metric_type, rpc, metric",
    [
        ("fib", "fib_summary", "pyez_junos_fib_routes"),
        ("pim", "pim_neighbors", "pyez_junos_pim_neighbors"),
    ],
)
def test_rejected_rpc_does_not_report_an_empty_table(tmp_path, metric_type, rpc, metric):
    found = samples(scrape(make_device(tmp_path, types=[metric_type])))
    assert metric not in found
    assert value(found, "pyez_junos_rpc_failed", rpc=rpc) == 1


def test_krt_from_text(found):
    assert value(found, "pyez_junos_krt_queue_entries", queue="normal_priority_add_queue") == 17
    assert value(found, "pyez_junos_krt_queue_entries", queue="routing_table_add_queue") == 0
    assert value(found, "pyez_junos_krt_state", field="number_of_operations_queued") == 17
    assert value(found, "pyez_junos_krt_state", field="routes_learned_from_kernel") == 12


def test_krt_queue_from_xml(tmp_path):
    (tmp_path / "krt_queue.xml").write_text(
        "<rpc-reply><krt-queue-information>"
        "<krt-queue><krtq-type>Normal-priority add queue</krtq-type>"
        "<krtq-queue-length>3</krtq-queue-length></krt-queue>"
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


def test_rpd_memory_accepts_a_flat_numeric_reply(tmp_path):
    (tmp_path / "task_memory.xml").write_text(
        "<task-memory-information><task-memory-in-use-size>1024</task-memory-in-use-size>"
        "<task-memory-in-use-avail>25</task-memory-in-use-avail></task-memory-information>"
    )
    device = make_device(tmp_path, types=["rpd_memory"])
    found = samples(scrape(device))
    assert value(found, "pyez_junos_rpd_task_memory", field="task_memory_in_use_size") == 1024
    assert value(found, "pyez_junos_rpd_task_memory", field="task_memory_in_use_avail") == 25
    assert not device.schema.missing


def test_pfe_exception_counters_are_summed_across_units(tmp_path):
    (tmp_path / "pfe_exceptions.xml").write_text(
        "<pfe-exceptions><unit><ttl-expired>3</ttl-expired></unit>"
        "<unit><ttl-expired>5</ttl-expired></unit></pfe-exceptions>"
    )
    device = make_device(tmp_path, types=["pfe_exceptions"])
    found = samples(scrape(device))
    assert value(found, "pyez_junos_pfe_exceptions_total", type="ttl-expired") == 8
    assert not device.schema.missing


def test_fib(found):
    assert value(found, "pyez_junos_fib_routes", table="default.inet", type="user") == 145
    assert value(found, "pyez_junos_fib_routes", table="default.inet6", type="user") == 98


def test_fib_ignores_empty_table_separators(tmp_path):
    reply = (SYNTHETIC / "fib_summary.xml").read_text().replace("<route-table>", "<route-table/><route-table>", 1)
    (tmp_path / "fib_summary.xml").write_text(reply)
    device = make_device(tmp_path, types=["fib"])
    found = samples(scrape(device))
    assert value(found, "pyez_junos_fib_routes", table="default.inet", type="user") == 145
    assert {labels["table"] for labels, _ in found["pyez_junos_fib_routes"]} == {"default.inet", "default.inet6"}
    assert not device.schema.missing


def test_neighbor_tables(found):
    assert value(found, "pyez_junos_arp_entries") == 2
    assert value(found, "pyez_junos_nd_entries", state="stale") == 2
    assert value(found, "pyez_junos_nd_entries", state="reachable") == 1
    assert value(found, "pyez_junos_nd_entries", state="incomplete") == 0


@pytest.mark.parametrize("entries", [0, 2])
def test_arp_counts_entries_when_summary_is_absent(tmp_path, entries):
    body = "<arp-table-entry><ip-address>192.0.2.1</ip-address></arp-table-entry>" * entries
    (tmp_path / "arp_table.xml").write_text(f"<arp-table-information>{body}</arp-table-information>")
    device = make_device(tmp_path, types=["neighbor_tables"])
    found = samples(scrape(device))
    assert value(found, "pyez_junos_arp_entries") == entries
    assert not device.schema.missing


def test_pim_exports_zero_for_an_interface_without_neighbors(tmp_path):
    (tmp_path / "pim_neighbors.xml").write_text(
        "<pim-neighbors-information><pim-interface><pim-interface-name>ae0.0</pim-interface-name>"
        "</pim-interface></pim-neighbors-information>"
    )
    device = make_device(tmp_path, types=["pim"])
    found = samples(scrape(device))
    assert value(found, "pyez_junos_pim_neighbors", interface="ae0.0") == 0
    assert "pyez_junos_pim_neighbor_up_seconds" not in found
    assert not device.schema.missing


def test_unparsable_text_is_reported_not_zero(tmp_path):
    (tmp_path / "pfe_hw_routes.xml").write_text("<rpc-reply><output>error: command is not valid</output></rpc-reply>")
    device = make_device(tmp_path, types=["pfe_hw_tables"])
    result = samples(scrape(device))
    assert "pyez_junos_pfe_hw_table_used_entries" not in result
    assert value(result, "pyez_junos_xml_missing_fields", collector="pfe_hw_routes", field="output:table-rows") == 1
