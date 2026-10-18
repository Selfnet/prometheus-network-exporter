"""Routing table metrics from ``show route summary`` and ``show route``.

``RouteSummaryCollector`` is cheap and covers every table. ``RouteTableCollector``
dumps the active routes of the configured tables, derives when the table last
changed from the route ages and exports details for a watch list of prefixes.
Its cost grows with the table size, so keep it to the tables that matter.
"""

from __future__ import annotations

import collections
from typing import Iterable

from prometheus_client.core import GaugeMetricFamily, InfoMetricFamily

from ..base import Collector
from . import base
from .rpcs import ROUTE_TABLE_RPC, route_destination_args, route_table_args
from .xmlutil import Reader, add, family_matches, find, findall, iter_items, label, text

TABLE_GAUGES = (
    ("destinations", "destination-count", "Destinations in the table"),
    ("routes", "total-route-count", "Routes in the table including inactive ones"),
    ("active_routes", "active-route-count", "Active routes in the table"),
    ("holddown_routes", "holddown-route-count", "Routes in holddown"),
    (
        "hidden_routes",
        "hidden-route-count",
        "Hidden routes, usually rejected by policy or with an unresolvable next hop",
    ),
)


class RouteSummaryCollector(Collector):
    name = "route_summary"

    def __init__(self, device):
        super().__init__(f"{base}_route", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        reply = self.device.rpc_reply("get_route_summary_information")
        if reply is None:
            return
        read = self.reader
        info = InfoMetricFamily(self.base_name, "Routing instance information")
        info.add_metric(
            [],
            {
                "router_id": label(read.text(reply, "router-id", required=False)),
                "as_number": label(read.text(reply, "as-number", required=False)),
            },
        )
        yield info

        gauges = {
            suffix: GaugeMetricFamily(
                f"{self.base_name}_table_{suffix}", doc, labels=["table"]
            )
            for suffix, _, doc in TABLE_GAUGES
        }
        protocol_routes = GaugeMetricFamily(
            f"{self.base_name}_table_protocol_routes",
            "Routes per protocol in the table",
            labels=["table", "protocol"],
        )
        protocol_active = GaugeMetricFamily(
            f"{self.base_name}_table_protocol_active_routes",
            "Active routes per protocol in the table",
            labels=["table", "protocol"],
        )
        for table in iter_items(reply, ("route-table",)):
            name = label(read.text(table, "table-name"))
            for suffix, field, _ in TABLE_GAUGES:
                add(gauges[suffix], [name], read.number(table, field))
            for protocol in findall(table, "protocols"):
                labels = [name, label(read.text(protocol, "protocol-name"))]
                add(protocol_routes, labels, read.number(protocol, "protocol-route-count"))
                add(protocol_active, labels, read.number(protocol, "active-route-count"))
        yield from read.unique((*gauges.values(), protocol_routes, protocol_active))


class WatchFamilies(collections.namedtuple(
    "WatchFamilies", "present age metric preference nexthops info"
)):
    """The metric families a watched prefix is exported into."""


def watch_families(base_name: str) -> WatchFamilies:
    labels = ["table", "prefix"]
    return WatchFamilies(
        GaugeMetricFamily(
            f"{base_name}_watch_present",
            "1 when the watched prefix has an active route in the table",
            labels=labels,
        ),
        GaugeMetricFamily(
            f"{base_name}_watch_age_seconds",
            "Age of the active route for the watched prefix",
            labels=labels,
        ),
        GaugeMetricFamily(
            f"{base_name}_watch_metric",
            "Metric of the active route for the watched prefix",
            labels=labels,
        ),
        GaugeMetricFamily(
            f"{base_name}_watch_preference",
            "Route preference of the active route for the watched prefix",
            labels=labels,
        ),
        GaugeMetricFamily(
            f"{base_name}_watch_nexthops",
            "Next hops of the active route for the watched prefix",
            labels=labels,
        ),
        InfoMetricFamily(
            f"{base_name}_watch",
            "Protocol and next hops of the active route for the watched prefix",
            labels=labels,
        ),
    )


def active_entry(reader: Reader, route):
    """The entry Junos marks as active, None when no entry is marked.

    With ``active-path`` every returned entry carries a marker. An unmarked
    entry is never treated as active: a prefix then counts as not present
    and the missing marker is recorded as a schema gap.
    """
    entries = findall(route, "rt-entry")
    for entry in entries:
        if find(entry, "current-active") is not None:
            return entry
        if (text(entry, "active-tag") or "") == "*":
            return entry
    if entries:
        reader.record("rt-entry/active-tag")
    return None


def emit_watch(read: Reader, families: WatchFamilies, labels, entry, protocol, route_age):
    """Export the active route of one watched prefix."""
    families.present.add_metric(labels, 1.0)
    add(families.age, labels, route_age)
    add(families.metric, labels, read.number(entry, "metric", required=False))
    add(families.preference, labels, read.number(entry, "preference"))
    hops = findall(entry, "nh")
    families.nexthops.add_metric(labels, float(len(hops)))
    families.info.add_metric(
        labels,
        {
            "protocol": protocol,
            "nexthop": ",".join(sorted(filter(None, (text(hop, "to") for hop in hops)))),
            "via": ",".join(
                sorted(
                    filter(
                        None,
                        (text(hop, "via") or text(hop, "nh-local-interface") for hop in hops),
                    )
                )
            ),
            "learned_from": label(text(entry, "learned-from")),
            "as_path": label(text(entry, "as-path")),
        },
    )


class RouteTableCollector(Collector):
    name = "route_table"

    def __init__(
        self,
        device,
        tables: Iterable[str],
        watch: Iterable[str] = (),
        young_seconds: float = 300.0,
    ):
        self.tables = list(tables)
        self.watch = list(watch)
        self.young_seconds = float(young_seconds)
        super().__init__(f"{base}_route", device, config={})
        self.reader = Reader(device.schema, self.name)

    def _active_entry(self, route):
        return active_entry(self.reader, route)

    def collect(self):
        read = self.reader
        threshold = GaugeMetricFamily(
            f"{self.base_name}_young_threshold_seconds",
            "Age below which a route counts as young",
        )
        threshold.add_metric([], self.young_seconds)
        newest = GaugeMetricFamily(
            f"{self.base_name}_newest_age_seconds",
            "Age of the youngest active route; small values mean the table "
            "changed recently",
            labels=["table", "protocol"],
        )
        young = GaugeMetricFamily(
            f"{self.base_name}_young_routes",
            "Active routes younger than the young threshold",
            labels=["table", "protocol"],
        )
        families = watch_families(self.base_name)

        for table in self.tables:
            reply = self.device.rpc_reply(ROUTE_TABLE_RPC, **route_table_args(table))
            if reply is None:
                # Unknown is not "missing": no watch samples for this table.
                # pyez_junos_rpc_failed{rpc="route_table_<name>"} reports it
                # and the JunosWatchedRouteUnknown rule alerts on that.
                continue
            watched = [prefix for prefix in self.watch if family_matches(prefix, table)]
            seen = set()
            newest_age = {}
            young_count = collections.Counter()
            for route in iter_items(reply, ("rt",)):
                destination = read.text(route, "rt-destination")
                entry = self._active_entry(route)
                if entry is None:
                    continue
                protocol = label(read.text(entry, "protocol-name"))
                route_age = read.seconds(entry, "age")
                young_count[protocol] += 0
                if route_age is not None:
                    newest_age[protocol] = min(newest_age.get(protocol, route_age), route_age)
                    if route_age < self.young_seconds:
                        young_count[protocol] += 1
                if destination not in watched or destination in seen:
                    continue
                seen.add(destination)
                emit_watch(read, families, [table, destination], entry, protocol, route_age)
            for protocol, count in sorted(young_count.items()):
                add(newest, [table, protocol], newest_age.get(protocol))
                young.add_metric([table, protocol], float(count))
            for prefix in watched:
                if prefix not in seen:
                    families.present.add_metric([table, prefix], 0.0)

        # Without a watch list the families stay out of the output, so that
        # RouteWatchCollector can own them without duplicate metadata.
        yield from read.unique(
            (threshold, newest, young, *(families if self.watch else ()))
        )


class RouteWatchCollector(Collector):
    """Watched prefixes looked up one by one with ``show route <prefix> exact``.

    Costs one small RPC per prefix instead of a full table dump, which makes
    it usable on border routers with large tables. Exports the same
    ``route_watch_*`` metrics as ``RouteTableCollector``; the device disables
    the watch list there when this collector is enabled.
    """

    name = "route_watch"

    def __init__(self, device, watch: Iterable[str], tables: Iterable[str] = ("inet.0", "inet6.0")):
        self.watch = list(watch)
        self.tables = list(tables)
        super().__init__(f"{base}_route", device, config={})
        self.reader = Reader(device.schema, self.name)

    def _table_for(self, prefix: str) -> str:
        for table in self.tables:
            if family_matches(prefix, table):
                return table
        return "inet6.0" if ":" in prefix else "inet.0"

    def collect(self):
        read = self.reader
        families = watch_families(self.base_name)
        for prefix in self.watch:
            table = self._table_for(prefix)
            reply = self.device.rpc_reply(ROUTE_TABLE_RPC, **route_destination_args(prefix, table))
            if reply is None:
                # Unknown, not absent: no sample, rpc_failed reports it.
                continue
            labels = [table, prefix]
            for route in iter_items(reply, ("rt",)):
                if read.text(route, "rt-destination") != prefix:
                    continue
                entry = active_entry(read, route)
                if entry is None:
                    continue
                emit_watch(
                    read, families, labels, entry,
                    label(read.text(entry, "protocol-name")),
                    read.seconds(entry, "age"),
                )
                break
            else:
                families.present.add_metric(labels, 0.0)
        yield from read.unique(families)
