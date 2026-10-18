# prometheus_network_exporter

## Install Requirements

```bash
    pip install .
```

## The Exporter

### Configuration

The configuration is under `/etc/prometheus-junos-exporter/config.yml` you should change the configuration.
No configuration means, that the current logged in user is used and its configuration.
The SSH config is also used.

#### example

```bash
    python -m prometheus_network_exporter.app
```

## HowTo: Query for junos_devices

    http://localhost:9332/metrics?target=device.example.com&module=default

If access is True only the interfaces for the ports specified in
`config/metrics_definitions.yml` are queried and if access is False everything is queried.
The default definition for access=True is:

## HowTo: disconnect all devices in Connection Pool?

This curl disconnects all devices currently in the exporter_connection_pool.

```bash
    curl "localhost:9332/disconnect"
```


```yml
NETWORK_REGEXES:
    - ge-*/1/*
    - xe-*/*/*
```

Those are backbone ports on our access switches. So access defines if it is a backbone switch/router or a access switch.

## Routing metrics for Junos (BGP, OSPF, route tables, BFD)

The metric types `bgp`, `ospf`, `routes` and `bfd` export the state of the
control plane. Everything is prefixed with `pyez_junos_`:

| Type | Collectors | Highlights |
|---|---|---|
| `bgp` | legacy summary, `bgp_peer_*`, `bgp_rib_*`, `bgp_group_*` | peer state as a state set, flap counter, per RIB prefix counts, message and error counters, uptime |
| `ospf` | statistics, `ospf_neighbor_*`, `ospf_interface_*`, `ospf_*` overview, `ospf_database_*`, `ospf_routes`; the same for `ospf3_` | neighbour state set and timers, interface cost and state, full SPF run counter, LSA counts, routes per next-hop interface |
| `routes` | `route_table_*`, `route_newest_age_seconds`, `route_young_routes`, `route_watch_*` | counts per table and protocol, time since the table changed, details for watched prefixes |
| `bfd` | `bfd_session_*` | session state, timers, diagnostics |

An optional `routing` block in the module configures the route table dump:

```yml
  routing:
    tables: [inet.0, inet6.0]        # tables to dump for ages and watched prefixes
    watch: ["0.0.0.0/0", "::/0"]      # prefixes that get present/age/next-hop metrics
    young_route_seconds: 300          # a route younger than this counts as young
```

Two metrics report the health of the scrape itself: `pyez_junos_rpc_failed`
lists RPCs Junos rejected, `pyez_junos_xml_missing_fields` counts fields a
collector expected but did not find in the reply. A field that is missing is
never exported as 0.

Deprecated: `pyez_junos_bgp_prefixes_received_total` and
`pyez_junos_bgp_prefixes_received_accepted_total` are gauges declared as
counters. They now sum over all RIBs of a peer; use
`pyez_junos_bgp_peer_rib_received_prefixes` instead.

## Look for prometheus config

Example config for your prometheus can be found under `prometheus/*`.

## For Enthusiasts

You can also configure the metrics definitions.
If their are not enough Metrics.
Configure `config/metrics_definitions.yml` and add functions to junos_exporter if the ouput is non trivial.

Interfaces, environment, IGMP, BGP, OSPF, route tables and BFD are supported.
So only the Metrics Counter, Gauge and Info are implemented.
Feel free to add Pull Requests to extend the implementation.
