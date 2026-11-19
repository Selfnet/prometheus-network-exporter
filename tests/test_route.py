from .conftest import labels_of, make_device, samples, scrape, value


def test_watch_ignores_other_prefixes_and_inactive_entries(tmp_path):
    (tmp_path / "route_destination_inet.0_0.0.0.0_0.xml").write_text(
        "<route-information><route-table><table-name>inet.0</table-name>"
        "<rt><rt-destination>192.0.2.0/24</rt-destination><rt-entry><active-tag>*</active-tag>"
        "</rt-entry></rt><rt><rt-destination>0.0.0.0/0</rt-destination>"
        "<rt-entry><inactive-reason>Not Best in its group - Router ID</inactive-reason></rt-entry>"
        "</rt></route-table></route-information>"
    )
    device = make_device(tmp_path, types=["route_watch"], options={"watch": ["0.0.0.0/0"], "tables": ["inet.0"]})
    found = samples(scrape(device))
    assert value(found, "pyez_junos_route_watch_present", table="inet.0", prefix="0.0.0.0/0") == 0
    assert "pyez_junos_route_watch_age_seconds" not in found
    assert "pyez_junos_route_watch_info" not in found


def test_summary(synthetic):
    assert labels_of(synthetic, "pyez_junos_route_info") == {"router_id": "192.0.2.101", "as_number": "64497"}
    assert value(synthetic, "pyez_junos_route_table_routes", table="inet.0") == 150
    assert value(synthetic, "pyez_junos_route_table_hidden_routes", table="inet.0") == 2
    assert value(synthetic, "pyez_junos_route_table_protocol_routes", table="inet.0", protocol="BGP") == 70
    assert value(synthetic, "pyez_junos_route_table_protocol_active_routes", table="inet.0", protocol="BGP") == 45
    assert value(synthetic, "pyez_junos_route_table_active_routes", table="bgp.evpn.0") == 40


def test_change_detection_from_route_ages(synthetic):
    assert value(synthetic, "pyez_junos_route_young_threshold_seconds") == 300
    assert value(synthetic, "pyez_junos_route_newest_age_seconds", table="inet.0", protocol="BGP") == 120
    assert value(synthetic, "pyez_junos_route_newest_age_seconds", table="inet.0", protocol="OSPF") == 30
    assert value(synthetic, "pyez_junos_route_newest_age_seconds", table="inet.0", protocol="Direct") == 100000
    assert value(synthetic, "pyez_junos_route_young_routes", table="inet.0", protocol="OSPF") == 1
    assert value(synthetic, "pyez_junos_route_young_routes", table="inet.0", protocol="Direct") == 0
    assert value(synthetic, "pyez_junos_route_young_routes", table="inet6.0", protocol="OSPF3") == 1


def test_watch_list(synthetic):
    assert value(synthetic, "pyez_junos_route_watch_present", table="inet.0", prefix="0.0.0.0/0") == 1
    assert value(synthetic, "pyez_junos_route_watch_present", table="inet.0", prefix="203.0.113.0/25") == 0
    assert value(synthetic, "pyez_junos_route_watch_present", table="inet6.0", prefix="::/0") == 1
    assert value(synthetic, "pyez_junos_route_watch_age_seconds", table="inet.0", prefix="0.0.0.0/0") == 120
    assert value(synthetic, "pyez_junos_route_watch_preference", table="inet.0", prefix="0.0.0.0/0") == 170
    assert value(synthetic, "pyez_junos_route_watch_nexthops", table="inet.0", prefix="0.0.0.0/0") == 2
    info = labels_of(synthetic, "pyez_junos_route_watch_info", table="inet.0", prefix="0.0.0.0/0")
    assert info["protocol"] == "BGP"
    assert info["nexthop"] == "198.51.100.137,198.51.100.2"
    assert info["via"] == "ae0.0,irb.100"
    assert info["learned_from"] == "192.0.2.102"
    # IPv4 prefixes are never looked for in inet6.0 and the other way round.
    assert not [
        labels
        for labels, _ in synthetic["pyez_junos_route_watch_present"]
        if labels["table"] == "inet6.0" and labels["prefix"] == "0.0.0.0/0"
    ]
