"""Behaviour under bad input: nothing may silently pass as healthy."""

from lxml import etree
from prometheus_client.core import GaugeMetricFamily

from prometheus_network_exporter.collectors.junos import xmlutil
from prometheus_network_exporter.collectors.junos.route import RouteTableCollector

from .conftest import ROUTING_OPTIONS, SYNTHETIC, make_device, samples, scrape, value


def test_number_rejects_non_finite_text():
    assert xmlutil.number("12") == 12
    assert xmlutil.number("0x8000abcd") == 0x8000ABCD
    assert xmlutil.number("1.5") == 1.5
    for bad in ("nan", "inf", "-Infinity", "1e400", "", "abc", None):
        assert xmlutil.number(bad) is None


def test_state_set_keeps_label_values_fixed():
    metric = GaugeMetricFamily("x", "x", labels=["state"])
    assert xmlutil.state_set(metric, [], "Garbage", ("Up", "Down")) is False
    states = {s.labels["state"]: s.value for s in metric.samples}
    assert states == {"Up": 0.0, "Down": 0.0, "unknown": 1.0}
    metric = GaugeMetricFamily("x", "x", labels=["state"])
    assert xmlutil.state_set(metric, [], "down", ("Up", "Down")) is True
    states = {s.labels["state"]: s.value for s in metric.samples}
    assert states == {"Up": 0.0, "Down": 1.0, "unknown": 0.0}


def test_unique_drops_duplicate_series_and_records_them():
    watch = xmlutil.SchemaWatch()
    metric = GaugeMetricFamily("x", "x", labels=["a"])
    metric.add_metric(["1"], 1.0)
    metric.add_metric(["1"], 2.0)
    metric.add_metric(["2"], 3.0)
    (family,) = list(xmlutil.unique([metric], watch, "test"))
    assert [(s.labels["a"], s.value) for s in family.samples] == [("1", 1.0), ("2", 3.0)]
    assert watch.missing == {("test", "duplicate:x"): 1}


def _route_reply(entries_xml: str):
    return etree.fromstring(
        "<route-information><route-table><table-name>inet.0</table-name>"
        f"<rt><rt-destination>0.0.0.0/0</rt-destination>{entries_xml}</rt>"
        "</route-table></route-information>"
    )


def test_unmarked_route_entry_is_not_treated_as_active():
    device = make_device(SYNTHETIC, types=[])
    collector = RouteTableCollector(device, ["inet.0"], ["0.0.0.0/0"], 300)
    device.begin_scrape()
    device._rpc_cache[("get_route_information", (("active_path", True), ("table", "inet.0")))] = _route_reply(
        "<rt-entry><protocol-name>BGP</protocol-name><preference>170</preference>"
        '<age seconds="5">00:00:05</age><nh><to>198.51.100.2</to><via>ae0.0</via></nh></rt-entry>'
    )
    found = {}
    for family in collector.collect():
        for sample in family.samples:
            found[(sample.name, sample.labels.get("prefix"))] = sample.value
    assert found[("pyez_junos_route_watch_present", "0.0.0.0/0")] == 0
    assert ("pyez_junos_route_watch_age_seconds", "0.0.0.0/0") not in found
    assert device.schema.missing == {("route_table", "rt-entry/active-tag"): 1}


def test_watch_prefix_listed_twice_in_a_dump_is_exported_once():
    device = make_device(SYNTHETIC, types=[])
    collector = RouteTableCollector(device, ["inet.0"], ["0.0.0.0/0"], 300)
    device.begin_scrape()
    entry = (
        "<rt-entry><active-tag>*</active-tag><protocol-name>BGP</protocol-name>"
        '<preference>170</preference><age seconds="5">00:00:05</age>'
        "<nh><to>198.51.100.2</to><via>ae0.0</via></nh></rt-entry>"
    )
    reply = _route_reply(entry)
    reply[0].append(etree.fromstring(f"<rt><rt-destination>0.0.0.0/0</rt-destination>{entry}</rt>"))
    device._rpc_cache[("get_route_information", (("active_path", True), ("table", "inet.0")))] = reply
    present = [
        s for family in collector.collect() for s in family.samples if s.name == "pyez_junos_route_watch_present"
    ]
    assert len(present) == 1 and present[0].value == 1


def test_bgp_peer_in_a_routing_instance_gets_its_own_series(synthetic):
    assert value(synthetic, "pyez_junos_bgp_peer_flaps_total", peer="192.0.2.102", routing_instance="master") == 3


def test_collect_releases_the_cache_and_only_its_own_lock():
    device = make_device(SYNTHETIC, options=ROUTING_OPTIONS)
    code, status, payload = device.collect()
    assert (code, status) == (200, "OK")
    assert b"pyez_junos_route_watch_present" in payload
    assert device._rpc_cache == {}
    assert not device.lock.locked()

    # A scrape that finds the device locked must neither unlock it nor close
    # the session of the scrape that holds it.
    assert device.lock.acquire(False)
    closed = []
    device.device.close = lambda: closed.append(True)
    try:
        error = None
        try:
            device.collect()
        except Exception as caught:  # noqa: BLE001
            error = caught
        assert error is not None and "locked" in str(error)
        assert device.lock.locked()
        assert closed == []
    finally:
        device.lock.release()


def test_unknown_states_are_counted_not_labelled(tmp_path):
    for path in SYNTHETIC.glob("*.xml"):
        text = path.read_text()
        if path.name == "ospf_neighbor.xml":
            text = text.replace(
                "<ospf-neighbor-state>2Way</ospf-neighbor-state>", "<ospf-neighbor-state>Weird</ospf-neighbor-state>"
            )
        (tmp_path / path.name).write_text(text)
    found = samples(scrape(make_device(tmp_path, types=["ospf_details"])))
    assert value(found, "pyez_junos_ospf_neighbor_state", neighbor_id="192.0.2.109", state="unknown") == 1
    assert "Weird" not in {labels["state"] for labels, _ in found["pyez_junos_ospf_neighbor_state"]}
    assert (
        value(
            found,
            "pyez_junos_xml_missing_fields",
            collector="ospf_neighbor",
            field="ospf-neighbor-state:unexpected-value",
        )
        == 1
    )
