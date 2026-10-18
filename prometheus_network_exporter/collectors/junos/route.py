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
from .rpcs import ROUTE_TABLE_RPC, route_table_args
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
        """The entry Junos marks as active, None when no entry is marked.

        With ``active-path`` every returned entry carries a marker. An
        unmarked entry is never treated as active: a prefix then counts as
        not present and the missing marker is recorded as a schema gap.
        """
        entries = findall(route, "rt-entry")
        for entry in entries:
            if find(entry, "current-active") is not None:
                return entry
            if (text(entry, "active-tag") or "") == "*":
                return entry
        if entries:
            self.reader.record("rt-entry/active-tag")
        return None

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
        watch_labels = ["table", "prefix"]
        present = GaugeMetricFamily(
            f"{self.base_name}_watch_present",
            "1 when the watched prefix has an active route in the table",
            labels=watch_labels,
        )
        age = GaugeMetricFamily(
            f"{self.base_name}_watch_age_seconds",
            "Age of the active route for the watched prefix",
            labels=watch_labels,
        )
        metric = GaugeMetricFamily(
            f"{self.base_name}_watch_metric",
            "Metric of the active route for the watched prefix",
            labels=watch_labels,
        )
        preference = GaugeMetricFamily(
            f"{self.base_name}_watch_preference",
            "Route preference of the active route for the watched prefix",
            labels=watch_labels,
        )
        nexthops = GaugeMetricFamily(
            f"{self.base_name}_watch_nexthops",
            "Next hops of the active route for the watched prefix",
            labels=watch_labels,
        )
        info = InfoMetricFamily(
            f"{self.base_name}_watch",
            "Protocol and next hops of the active route for the watched prefix",
            labels=watch_labels,
        )

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
                labels = [table, destination]
                present.add_metric(labels, 1.0)
                add(age, labels, route_age)
                add(metric, labels, read.number(entry, "metric", required=False))
                add(preference, labels, read.number(entry, "preference"))
                hops = findall(entry, "nh")
                nexthops.add_metric(labels, float(len(hops)))
                info.add_metric(
                    labels,
                    {
                        "protocol": protocol,
                        "nexthop": ",".join(
                            sorted(filter(None, (text(hop, "to") for hop in hops)))
                        ),
                        "via": ",".join(
                            sorted(
                                filter(
                                    None,
                                    (
                                        text(hop, "via") or text(hop, "nh-local-interface")
                                        for hop in hops
                                    ),
                                )
                            )
                        ),
                        "learned_from": label(text(entry, "learned-from")),
                        "as_path": label(text(entry, "as-path")),
                    },
                )
            for protocol, count in sorted(young_count.items()):
                add(newest, [table, protocol], newest_age.get(protocol))
                young.add_metric([table, protocol], float(count))
            for prefix in watched:
                if prefix not in seen:
                    present.add_metric([table, prefix], 0.0)

        yield from read.unique(
            (threshold, newest, young, present, age, metric, preference, nexthops, info)
        )
