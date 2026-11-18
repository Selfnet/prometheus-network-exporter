"""Structural checks that run against every fixture directory.

A capture placed in tests/fixtures/junos/<host>/ is checked as well and these
tests tell whether the collectors understand that Junos release: no missing
fields, valid exposition, unique metric families. Such captures stay local,
.gitignore keeps them out of the repository.
"""

import pytest
from prometheus_client.parser import text_string_to_metric_families

from prometheus_network_exporter.collectors.junos.bfd import BFDCollector
from prometheus_network_exporter.collectors.junos.bgp_neighbor import BGPNeighborCollector
from prometheus_network_exporter.collectors.junos.bgp_overview import BGPOverviewCollector
from prometheus_network_exporter.collectors.junos.ospf_database import OSPFDatabaseCollector
from prometheus_network_exporter.collectors.junos.ospf_interface import OSPFInterfaceCollector
from prometheus_network_exporter.collectors.junos.ospf_neighbor import OSPFNeighborCollector
from prometheus_network_exporter.collectors.junos.ospf_overview import OSPFOverviewCollector
from prometheus_network_exporter.collectors.junos.ospf_route import OSPFRouteCollector
from prometheus_network_exporter.collectors.junos.route import RouteSummaryCollector, RouteTableCollector

from .conftest import ALL_TYPES, ROUTING_OPTIONS, SYNTHETIC, fixture_sets, make_device, samples, scrape

FIXTURE_IDS = [path.name for path in fixture_sets()]


@pytest.mark.parametrize("fixture_dir", fixture_sets(), ids=FIXTURE_IDS)
def test_no_schema_gaps_and_valid_exposition(fixture_dir):
    device = make_device(fixture_dir, types=ALL_TYPES, options=ROUTING_OPTIONS)
    text = scrape(device)
    families = list(text_string_to_metric_families(text))
    names = [family.name for family in families]
    assert len(names) == len(set(names)), "metric family exported twice"
    found = samples(text)
    missing = [
        (labels["collector"], labels["field"]) for labels, v in found.get("pyez_junos_xml_missing_fields", []) if v
    ]
    assert missing == [], f"collectors expect fields this Junos reply does not have: {missing}"


def test_every_rpc_is_run_once_per_scrape():
    device = make_device(SYNTHETIC, types=ALL_TYPES, options=ROUTING_OPTIONS)
    scrape(device)
    calls = device.device.rpc.calls
    # The legacy BGP collector uses a PyEZ table and bypasses the cache, so
    # bgp_summary is the one RPC allowed twice.
    duplicates = sorted(name for name in set(calls) if calls.count(name) > 1)
    assert duplicates == ["bgp_summary"]
    assert set(device.rpc_durations) >= {"bgp_neighbor", "ospf_overview", "route_table_inet.0", "bfd_session"}
    assert device.rpc_failed == set()


def test_second_scrape_starts_clean():
    device = make_device(SYNTHETIC, types=ALL_TYPES, options=ROUTING_OPTIONS)
    first = samples(scrape(device))
    second = samples(scrape(device))
    # Wall clock durations differ between runs, everything else must not.
    for timing in (
        "pyez_junos_rpc_duration_seconds",
        "pyez_junos_collector_duration_seconds",
        "pyez_junos_probe_rpc_seconds",
    ):
        first.pop(timing)
        second.pop(timing)
    assert first == second


def _new_collectors(device):
    yield BGPNeighborCollector(device)
    yield BGPOverviewCollector(device)
    for protocol in ("ospf", "ospf3"):
        yield OSPFNeighborCollector(device, protocol)
        yield OSPFInterfaceCollector(device, protocol)
        yield OSPFOverviewCollector(device, protocol)
        yield OSPFDatabaseCollector(device, protocol)
        yield OSPFRouteCollector(device, protocol, watch=ROUTING_OPTIONS["watch"])
    yield RouteSummaryCollector(device)
    yield RouteTableCollector(device, ROUTING_OPTIONS["tables"], ROUTING_OPTIONS["watch"], 300)
    yield BFDCollector(device)


def _collect_all(strip):
    device = make_device(SYNTHETIC, types=[], options=ROUTING_OPTIONS, strip=strip)
    device.begin_scrape()
    result = {}
    for collector in _new_collectors(device):
        for family in collector.collect():
            for sample in family.samples:
                result[(sample.name, tuple(sorted(sample.labels.items())))] = sample.value
    assert not device.schema.missing
    return result


def test_namespaced_and_stripped_replies_give_identical_samples():
    # Before any PyEZ table ran the reply still carries the Junos namespaces.
    assert _collect_all(strip=False) == _collect_all(strip=True)
