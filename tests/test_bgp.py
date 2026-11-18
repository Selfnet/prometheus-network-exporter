from .conftest import labels_of, value


def test_peer_state_is_a_state_set(synthetic):
    assert value(synthetic, "pyez_junos_bgp_peer_state", peer="192.0.2.102", state="Established") == 1
    assert value(synthetic, "pyez_junos_bgp_peer_state", peer="192.0.2.102", state="Active") == 0
    assert value(synthetic, "pyez_junos_bgp_peer_state", peer="192.0.2.105", state="Active") == 1
    assert value(synthetic, "pyez_junos_bgp_peer_state", peer="192.0.2.105", state="Established") == 0


def test_peer_labels_strip_the_port_and_resolve_names(synthetic):
    labels = labels_of(synthetic, "pyez_junos_bgp_peer_flaps_total", peer="192.0.2.102")
    assert labels == {
        "peer": "192.0.2.102",
        "peername": "name-of-192.0.2.102",
        "group": "iBGP-RR",
        "routing_instance": "master",
    }


def test_uptime_comes_from_the_summary(synthetic):
    assert value(synthetic, "pyez_junos_bgp_peer_state_seconds", peer="192.0.2.102") == 864000
    assert value(synthetic, "pyez_junos_bgp_peer_state_seconds", peer="192.0.2.105") == 120


def test_flaps_messages_and_errors(synthetic):
    assert value(synthetic, "pyez_junos_bgp_peer_flaps_total", peer="192.0.2.105") == 7
    assert value(synthetic, "pyez_junos_bgp_peer_updates_total", peer="192.0.2.102", direction="in") == 234
    assert value(synthetic, "pyez_junos_bgp_peer_octets_total", peer="192.0.2.102", direction="out") == 400000
    assert value(
        synthetic,
        "pyez_junos_bgp_peer_errors_total",
        peer="192.0.2.102",
        error="Hold Timer Expired Error",
        direction="in",
    ) == 2
    assert value(synthetic, "pyez_junos_bgp_peer_errors_total", peer="192.0.2.102", error="Cease", direction="out") == 0


def test_every_rib_of_a_peer_is_exported(synthetic):
    assert value(synthetic, "pyez_junos_bgp_peer_rib_received_prefixes", peer="192.0.2.102", rib="inet.0") == 15
    assert value(synthetic, "pyez_junos_bgp_peer_rib_received_prefixes", peer="192.0.2.102", rib="bgp.evpn.0") == 42
    assert value(synthetic, "pyez_junos_bgp_peer_rib_advertised_prefixes", peer="192.0.2.102", rib="bgp.evpn.0") == 18
    assert value(synthetic, "pyez_junos_bgp_peer_output_queue_routes", peer="192.0.2.102", rib="bgp.evpn.0") == 2
    # A peer that is not Established has no RIBs and no negotiated timers.
    assert not [l for l, _ in synthetic["pyez_junos_bgp_peer_rib_received_prefixes"] if l["peer"] == "192.0.2.105"]
    assert not [l for l, _ in synthetic["pyez_junos_bgp_peer_hold_time_seconds"] if l["peer"] == "192.0.2.105"]
    assert value(synthetic, "pyez_junos_bgp_peer_hold_time_seconds", peer="192.0.2.102") == 90


def test_info_and_last_event(synthetic):
    info = labels_of(synthetic, "pyez_junos_bgp_peer_info", peer="192.0.2.102")
    assert info["peer_as"] == "64497"
    assert info["peer_type"] == "Internal"
    assert info["local_address"] == "192.0.2.101"
    assert info["address_families"] == "inet-unicast evpn"
    assert info["description"] == "core-2"
    event = labels_of(synthetic, "pyez_junos_bgp_peer_last_event_info", peer="192.0.2.105")
    assert event["last_error"] == "Hold Timer Expired Error"
    assert event["last_flap_event"] == "HoldTime"


def test_device_level_summary_and_groups(synthetic):
    assert value(synthetic, "pyez_junos_bgp_peers") == 3
    assert value(synthetic, "pyez_junos_bgp_peers_down") == 1
    assert value(synthetic, "pyez_junos_bgp_groups") == 2
    assert value(synthetic, "pyez_junos_bgp_rib_active_prefixes", rib="bgp.evpn.0") == 40
    assert value(synthetic, "pyez_junos_bgp_rib_pending_prefixes", rib="bgp.evpn.0") == 1
    assert value(synthetic, "pyez_junos_bgp_group_peers", group="iBGP-RR", type="Internal") == 3
    assert value(synthetic, "pyez_junos_bgp_group_established_peers", group="iBGP-RR") == 2


def test_legacy_bgp_metrics_sum_over_all_ribs(synthetic):
    # inet.0 (15) + bgp.evpn.0 (42) instead of the first RIB only.
    assert value(synthetic, "pyez_junos_bgp_prefixes_received_total", neighbor="192.0.2.102") == 57
    assert value(synthetic, "pyez_junos_bgp_is_up_status", neighbor="192.0.2.105") == 0
    assert value(synthetic, "pyez_junos_bgp_is_up_status", neighbor="192.0.2.102") == 1


def test_down_peer_without_message_counters_is_no_schema_gap(tmp_path):
    from .conftest import make_device, samples, scrape

    (tmp_path / "bgp_neighbor.xml").write_text(
        "<rpc-reply><bgp-information><bgp-peer>"
        "<peer-address>2001:db8:0:8010::1+179</peer-address><peer-as>65454</peer-as>"
        "<peer-group>iBGP-RR</peer-group><peer-state>Active</peer-state>"
        "<flap-count>0</flap-count><description>ar1-10a-1</description>"
        "</bgp-peer></bgp-information></rpc-reply>"
    )
    device = make_device(tmp_path, types=["bgp_details"])
    found = samples(scrape(device))
    assert not [k for k in device.schema.missing if k[0] == "bgp_neighbor" and "messages" in k[1]]
    assert "pyez_junos_bgp_peer_messages_total" not in found
