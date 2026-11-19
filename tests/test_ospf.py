import pytest

from prometheus_network_exporter.collectors.junos.ospf_database import OSPFDatabaseCollector
from prometheus_network_exporter.collectors.junos.ospf_interface import OSPFInterfaceCollector
from prometheus_network_exporter.collectors.junos.ospf_neighbor import OSPFNeighborCollector
from prometheus_network_exporter.collectors.junos.ospf_overview import OSPFOverviewCollector
from prometheus_network_exporter.collectors.junos.ospf_route import OSPFRouteCollector
from prometheus_network_exporter.collectors.junos.ospf_statistics import OSPFStatisticsCollector

from .conftest import SYNTHETIC, labels_of, make_device, samples, scrape, value


@pytest.mark.parametrize(
    "collector_type",
    [
        OSPFDatabaseCollector,
        OSPFInterfaceCollector,
        OSPFNeighborCollector,
        OSPFOverviewCollector,
        OSPFRouteCollector,
        OSPFStatisticsCollector,
    ],
)
def test_unsupported_protocol_is_rejected_before_an_rpc(collector_type):
    device = make_device(SYNTHETIC, types=[])
    with pytest.raises(ValueError, match="Unsupported OSPF protocol: ospf4"):
        collector_type(device, protocol="ospf4")
    assert device.device.rpc.calls == []


def test_database_ignores_xml_comments(tmp_path):
    reply = (
        (SYNTHETIC / "ospf_database.xml")
        .read_text()
        .replace("<ospf-database>", "<!-- database entry --><ospf-database>", 1)
    )
    (tmp_path / "ospf_database.xml").write_text(reply)
    found = samples(scrape(make_device(tmp_path, types=["ospf_details"])))
    assert value(found, "pyez_junos_ospf_database_lsas", area="0.0.0.0", lsa_type="Router") == 3
    assert not found.get("pyez_junos_collector_failed")


def test_unknown_interface_state_is_reported(tmp_path):
    reply = (
        (SYNTHETIC / "ospf_interface.xml")
        .read_text()
        .replace(
            "<ospf-interface-state>PtToPt</ospf-interface-state>",
            "<ospf-interface-state>Unexpected</ospf-interface-state>",
            1,
        )
    )
    (tmp_path / "ospf_interface.xml").write_text(reply)
    found = samples(scrape(make_device(tmp_path, types=["ospf_details"])))
    assert value(found, "pyez_junos_ospf_interface_state", interface="ae0.0", state="unknown") == 1
    assert (
        value(
            found,
            "pyez_junos_xml_missing_fields",
            collector="ospf_interface",
            field="ospf-interface-state:unexpected-value",
        )
        == 1
    )


def test_neighbor_state_set_and_timers(synthetic):
    assert value(synthetic, "pyez_junos_ospf_neighbor_state", interface="ae0.0", state="Full") == 1
    assert value(synthetic, "pyez_junos_ospf_neighbor_state", neighbor_id="192.0.2.109", state="2Way") == 1
    assert value(synthetic, "pyez_junos_ospf_neighbor_state", neighbor_id="192.0.2.109", state="Full") == 0
    assert value(synthetic, "pyez_junos_ospf_neighbor_up_seconds", neighbor_id="192.0.2.102") == 864000
    assert value(synthetic, "pyez_junos_ospf_neighbor_adjacency_seconds", neighbor_id="192.0.2.117") == 7190
    assert value(synthetic, "pyez_junos_ospf_neighbor_dead_timer_seconds", neighbor_id="192.0.2.109") == 38
    assert value(synthetic, "pyez_junos_ospf_neighbor_priority", neighbor_id="192.0.2.109") == 1


def test_two_neighbors_on_one_interface_are_both_exported(synthetic):
    on_irb = [
        labels
        for labels, _ in synthetic["pyez_junos_ospf_neighbor_dead_timer_seconds"]
        if labels["interface"] == "irb.100"
    ]
    assert {labels["neighbor_id"] for labels in on_irb} == {"192.0.2.109", "192.0.2.117"}
    info = labels_of(synthetic, "pyez_junos_ospf_neighbor_info", neighbor_id="192.0.2.109")
    assert info["dr"] == "198.51.100.129"
    assert info["bdr"] == "198.51.100.145"
    assert info["neighbor_name"] == "name-of-192.0.2.109"


def test_ospf3_neighbor_uses_dr_id(synthetic):
    assert value(synthetic, "pyez_junos_ospf3_neighbor_up_seconds", neighbor_id="192.0.2.102") == 86400
    info = labels_of(synthetic, "pyez_junos_ospf3_neighbor_info", neighbor_id="192.0.2.102")
    assert info["dr"] == "0.0.0.0"
    assert info["neighbor_address"] == "fe80::1"


def test_interfaces(synthetic):
    assert value(synthetic, "pyez_junos_ospf_interface_state", interface="ae0.0", state="PtToPt") == 1
    assert value(synthetic, "pyez_junos_ospf_interface_state", interface="irb.100", state="DR") == 1
    assert value(synthetic, "pyez_junos_ospf_interface_cost", interface="irb.100") == 100
    assert value(synthetic, "pyez_junos_ospf_interface_neighbors", interface="irb.100") == 2
    assert value(synthetic, "pyez_junos_ospf_interface_adjacencies", interface="irb.100") == 1
    assert value(synthetic, "pyez_junos_ospf_interface_dead_interval_seconds", interface="ae0.0") == 40
    assert value(synthetic, "pyez_junos_ospf_interface_mtu_bytes", interface="ae0.0") == 9000
    assert labels_of(synthetic, "pyez_junos_ospf_interface_info", interface="lo0.0")["passive"] == "yes"
    assert labels_of(synthetic, "pyez_junos_ospf_interface_info", interface="irb.100")["authentication"] == "MD5"
    assert value(synthetic, "pyez_junos_ospf3_interface_cost", interface="ae0.0") == 10


def test_overview(synthetic):
    assert labels_of(synthetic, "pyez_junos_ospf_info")["router_id"] == "192.0.2.101"
    assert value(synthetic, "pyez_junos_ospf_full_spf_runs_total", topology="default") == 1234
    assert value(synthetic, "pyez_junos_ospf3_full_spf_runs_total", topology="default") == 77
    assert value(synthetic, "pyez_junos_ospf_spf_delay_seconds", topology="default") == pytest.approx(0.2)
    assert value(synthetic, "pyez_junos_ospf_exported_prefixes", topology="default") == 4
    assert value(synthetic, "pyez_junos_ospf_area_neighbors_up", area="0.0.0.0") == 3
    assert value(synthetic, "pyez_junos_ospf_area_asbrs", area="0.0.0.0") == 2
    assert labels_of(synthetic, "pyez_junos_ospf_area_info", area="0.0.0.0")["stub_type"] == "Not Stub"


def test_database_aggregates(synthetic):
    assert value(synthetic, "pyez_junos_ospf_database_lsas", area="0.0.0.0", lsa_type="Router") == 3
    assert value(synthetic, "pyez_junos_ospf_database_own_lsas", area="0.0.0.0", lsa_type="Router") == 1
    assert value(synthetic, "pyez_junos_ospf_database_own_lsas", area="0.0.0.0", lsa_type="Network") == 1
    assert value(synthetic, "pyez_junos_ospf_database_lsas", area="external", lsa_type="Extern") == 2
    assert value(synthetic, "pyez_junos_ospf_database_lsa_age_seconds_min", area="external", lsa_type="Extern") == 50
    assert value(synthetic, "pyez_junos_ospf_database_own_router_lsa_sequence", area="0.0.0.0") == 0x8000ABCD
    assert value(synthetic, "pyez_junos_ospf_database_own_router_lsa_age_seconds", area="0.0.0.0") == 120
    # OSPFv3 link LSAs follow an interface header that still names the area.
    assert value(synthetic, "pyez_junos_ospf3_database_lsas", area="0.0.0.0", lsa_type="Link") == 2
    assert value(synthetic, "pyez_junos_ospf3_database_own_lsas", area="0.0.0.0", lsa_type="Link") == 1


def test_routes_by_type_and_interface(synthetic):
    assert (
        value(
            synthetic,
            "pyez_junos_ospf_routes",
            area="0.0.0.0",
            path_type="Intra",
            route_type="Network",
            nexthop_interface="ae0.0",
        )
        == 2
    )
    assert (
        value(
            synthetic,
            "pyez_junos_ospf_routes",
            area="0.0.0.0",
            path_type="Intra",
            route_type="Network",
            nexthop_interface="irb.100",
        )
        == 1
    )
    assert (
        value(
            synthetic,
            "pyez_junos_ospf_routes",
            area="",
            path_type="Ext2",
            route_type="Network",
            nexthop_interface="irb.100",
        )
        == 1
    )
    assert value(synthetic, "pyez_junos_ospf_routes", path_type="Intra", route_type="Router") == 1
    # Watched prefixes carry cost and next hop; the family decides the protocol.
    assert (
        value(
            synthetic,
            "pyez_junos_ospf_route_cost",
            prefix="0.0.0.0/0",
            nexthop_interface="irb.100",
            nexthop="198.51.100.137",
        )
        == 0
    )
    assert value(synthetic, "pyez_junos_ospf3_route_cost", prefix="::/0", nexthop="fe80::2") == 0
    assert not [labels for labels, _ in synthetic["pyez_junos_ospf3_route_cost"] if labels["prefix"] == "0.0.0.0/0"]


def test_legacy_ospf_view_requests_extensive_and_keeps_both_neighbors():
    device = make_device(SYNTHETIC, types=["ospf"])
    device.begin_scrape()
    ospf = device.get_ospf()
    assert device.device.rpc.calls == ["ospf_neighbor"]
    units = ospf["irb"]["ospf"]
    assert {unit["neighbor_id"] for unit in units} == {"name-of-192.0.2.109", "name-of-192.0.2.117"}
    assert {unit["neighbor_up_time"] for unit in units} == {600, 7200}
    assert ospf["ae0"]["ospf"][0]["ospf_neighbor_state"] is True
    assert ospf["ae0"]["ospf"][0]["unit"] == 0


def test_missing_protocol_produces_no_metrics_but_a_failed_rpc(tmp_path):
    # Only OSPFv2 fixtures: every OSPFv3 RPC fails like on a device without OSPFv3.
    for name in ("ospf_neighbor", "ospf_interface", "ospf_overview", "ospf_database", "ospf_route", "ospf_statistics"):
        (tmp_path / f"{name}.xml").write_bytes((SYNTHETIC / f"{name}.xml").read_bytes())
    from .conftest import samples, scrape

    found = samples(scrape(make_device(tmp_path, types=["ospf_details"])))
    assert "pyez_junos_ospf3_neighbor_state" not in found
    assert value(found, "pyez_junos_ospf_full_spf_runs_total", topology="default") == 1234
    failed = {labels["rpc"] for labels, _ in found["pyez_junos_rpc_failed"]}
    assert failed == {
        "ospf3_neighbor",
        "ospf3_interface",
        "ospf3_overview",
        "ospf3_database",
        "ospf3_route",
        "ospf3_statistics",
    }
