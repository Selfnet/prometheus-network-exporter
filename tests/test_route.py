from .conftest import labels_of, value


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
