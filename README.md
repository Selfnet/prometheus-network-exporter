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

    http://localhost:9332/device?target=device.example.com&module=default

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

## Optics, transceiver inventory and link endpoints

The `optics` collector reads module diagnostics and every reported
`optics-diagnostics-lane-values` record from one RPC reply. The lane IDs and
count come from the reply, never from the interface speed. Breakout ports
keep their interface names, such as `xe-0/1/1:2`, and the reported lane ID.
A non-breakout interface can have one, four or another number of reported
lanes. A scalar-only reply does not establish the number of optical lanes.

Existing `pyez_junos_interface_*` optic metric names and labels remain.
Missing readings, including explicit `N/A`, are no longer emitted as zero.
A real zero remains zero; a reported `-Inf` remains `-Inf`. A single lane
also supplies the legacy interface readings when the mapping is unambiguous
(for breakout ports the suffix must match the lane ID). Multiple lanes are
never averaged into one interface reading.

Additional metrics (prefix `pyez_junos_interface_`):

| Metric | Meaning |
|---|---|
| `optics_available{interface}` | 1 for reported diagnostics, 0 for explicit N/A; absent when no usable diagnostic structure was returned |
| `optics_reported_lanes{interface}` | number of explicitly reported lane records on this interface; absent for scalar-only or unavailable diagnostics, not total module lane capacity |
| `lane_receiving_optic_power_dbm`, `lane_sending_optic_power_dbm` | RX/TX per `interface` and `lane`, with the existing description, MAC and speed labels |
| `lane_receiving_optic_power_*`, `lane_sending_optic_power_*` | reported alarm/warning thresholds; lane-specific thresholds override common module thresholds |
| `lane_laser_bias_current_milliamps`, `lane_laser_bias_*_threshold_milliamps` | bias current and thresholds per lane |
| `lane_optics_alarm{interface,lane,alarm}` | reported lane alarm and warning flags, 1=on and 0=off |
| `voltage_volts`, `voltage_*_threshold_volts` | module voltage and its alarm/warning thresholds |
| `laser_bias_current_milliamps`, `laser_bias_*_threshold_milliamps` | correctly named aliases for the legacy bias metrics |

The old voltage/bias metric names ending in `_dbm` are retained for existing
dashboards, but their values are volts/milliamps, not dBm. The historical
`receiving_optic_power_low_alarm_threshold` name still has no `_dbm` suffix;
the corresponding lane metric preserves that spelling. The legacy
`sending_laser_fault_alarm` uses 1=OK, 0=fault. Generic `optics_alarm` flags
use 1=alarm, 0=clear and include additional flags Junos reports.

Two optional types add inventory and addressing:

| Type | Metrics | Source and cost |
|---|---|---|
| `transceivers` | `pyez_junos_transceiver_info{module,manufacturer,part_number,serial_number,transceiver_type}` and `pyez_junos_interface_transceiver_info{interface,module}` | one chassis inventory RPC, one PIC detail RPC per PIC with transceivers, and one brief interface RPC |
| `interface_addresses` | `pyez_junos_interface_address_info{interface,parent_interface,routing_instance,address,family,prefix_length,network}` | one terse interface RPC, including logical units and IPv4/IPv6 |

`module` is the FPC/PIC/port location, e.g. `0/1/1`. Several breakout
interfaces map to the same module; serial numbers are not treated as unique
keys. PIC detail supplies vendor name and part number when available;
chassis inventory supplies serial number and reported type. Missing fields
are blank, not inferred from the switch vendor. Unresolvable chassis
locations are skipped. A failed PIC RPC leaves the chassis inventory usable.

Addresses without a known prefix retain a blank `prefix_length` and
`network`. A peer address without a prefix is not interpreted as a subnet.
An absent routing instance is unknown, not proof of the default instance.
`parent_interface` is the containing physical interface from the XML;
a LAG such as `ae0` is not assigned to an arbitrary member. These are inputs
for endpoint comparisons, not a proof that a cable or subnet is correct.

The existing `lldp` type now retains `remote_port_id`,
`remote_port_description` and `remote_port_subtype` separately in
`pyez_junos_lldp_neighbor_info`. Its existing `remote_port` label keeps the
old description-first fallback. The extra labels create new LLDP series
on upgrade; update joins that explicitly list all labels if needed.

Enable `lldp`, `transceivers` and `interface_addresses` in the relevant
module's `metrics` list. For split core scrapes, add inventory/addressing
only to `core_slow`; do not collect the same type in multiple modules for
the same target. Access and legacy backbone modules need their own entries.
The example config includes these types. RPC replies with identical
arguments are cached within each scrape, including brief interface replies
shared by standalone optics and inventory. No additional optics RPC is
issued per lane. The NETCONF login class must permit the new chassis/PIC
and interface queries. Rejected RPCs remain visible in `pyez_junos_rpc_failed`.

These collectors report device data; they do not infer a DAC from a hostname,
SFP-T label, N/A response or zero measurement.

Tests run without a switch:

```bash
python -m unittest discover -s tests -v
```

The recorded optics fixture covers four breakout lanes, scalar optics and
explicit N/A replies. Synthetic tests cover other lane counts, missing
fields, inventory and address replies. Inventory/PIC schemas and unbroken
multi-lane modules still need validation on the deployed device models.

## Routing metrics for Junos (BGP, OSPF, route tables, BFD)

The metric types `bgp`, `ospf`, `routes` and `bfd` export the state of the
control plane. `bgp` and `ospf` are the cheap views of 1.2.5; the detail
types cost ten more RPCs per scrape, among them `show bgp neighbor` and the
LSDB, and belong into a slow module. Everything is prefixed with `pyez_junos_`:

| Type | Collectors | Highlights |
|---|---|---|
| `bgp` | legacy summary (`bgp_is_up_status`, prefix counters) | one `show bgp summary`, as before 1.4 |
| `bgp_details` | `bgp_peer_*`, `bgp_rib_*`, `bgp_group_*` | peer state as a state set, flap counter, per RIB prefix counts, message and error counters, uptime |
| `ospf` | legacy neighbour state and uptime per interface | two neighbour tables, as before 1.4 |
| `ospf_details` | statistics, `ospf_neighbor_*`, `ospf_interface_*`, `ospf_*` overview, `ospf_database_*`, `ospf_routes`; the same for `ospf3_` | neighbour state set and timers, interface cost and state, full SPF run counter, LSA counts, routes per next-hop interface |
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

## Control plane, forwarding plane and link metrics for Junos

These types exist to locate control plane stalls and packet loss on core
switches. Every type has its own collector, so a module can be split by cost
into a fast and a slow scrape job (see `config/config.yml`, modules
`core_probe`, `core_fast` and `core_slow`).

| Type | Metrics (prefix `pyez_junos_`) | Source |
|---|---|---|
| `probe` | `probe_success`, `probe_rpc_seconds` | `show version`; one cheap RPC for a 15s responsiveness job |
| `routing_engine` | `re_cpu_ratio{mode,window}`, `re_load_average`, `re_memory_utilization_ratio`, `re_temperature_celsius`, `re_up_seconds`, `re_info` | `show chassis routing-engine` |
| `processes` | `process_cpu_ratio`, `process_resident_bytes`, `process_threads`, `processes` | `show system processes extensive`, a fixed daemon list plus the top N |
| `fpc` | `fpc_state`, `fpc_cpu_ratio`, `fpc_cpu_interrupt_ratio`, `fpc_memory_utilization_ratio`, `fpc_temperature_celsius` | `show chassis fpc` |
| `alarms` | `alarms_active{source,class}`, `alarm_info`, `alarm_since_timestamp_seconds` | `show chassis alarms`, `show system alarms` |
| `core_dumps` | `core_dumps{process}`, `core_dump_newest_timestamp_seconds` | `show system core-dumps` |
| `system` | `system_time_seconds`, `system_booted_timestamp_seconds`, `last_commit_timestamp_seconds`, `last_commit_info{user}`, `storage_used_ratio`, `ntp_synced`, `ntp_offset_seconds` | `show system uptime`, `show system storage`, `show ntp status` |
| `pfe` | `pfe_statistics_total{section,counter}`, `pfe_statistics_rate` | `show pfe statistics traffic` |
| `pfe_exceptions` | `pfe_exceptions_total{type}` | `show pfe statistics exceptions` (not on every platform) |
| `pfe_hw_tables` | `pfe_hw_table_max_entries`, `pfe_hw_table_used_entries` | `show pfe route summary hw` |
| `ddos` | `ddos_packets_total`, `ddos_rate_pps`, `ddos_violations`, `ddos_violation_active` | `show ddos-protection protocols statistics terse` and `violations` |
| `krt` | `krt_queue_entries{queue}`, `krt_state{field}` | `show krt queue`, `show krt state` |
| `rpd_memory` | `rpd_task_memory{field}` | `show task memory` |
| `fib` | `fib_routes{table,family,type}` | `show route forwarding-table summary` |
| `route_watch` | `route_watch_*` as with `routes`, one `show route <prefix> exact` per watched prefix and table of its address family | replaces the watch list of the table dump |
| `ldp` | `ldp_session_state`, `ldp_session_up_seconds`, `ldp_neighbors`, `ldp_neighbor_hold_remaining_seconds` | `show ldp session detail`, `show ldp neighbor` |
| `l2circuit` | `l2circuit_up`, `l2circuit_up_transitions_total`, `l2circuit_info` | `show l2circuit connections` |
| `pim` | `pim_neighbors`, `pim_neighbor_up_seconds` | `show pim neighbors` |
| `neighbor_tables` | `arp_entries`, `nd_entries{state}` | `show arp no-resolve`, `show ipv6 neighbors` |
| `interface_errors` | `interface_errors_total{list,counter}` (CRC, carrier transitions, MTU errors, resource errors, pause frames, ...), `interface_queue_packets_total{queue,forwarding_class,kind}` | `show interfaces extensive`, only ports whose description matches |
| `logical_interfaces` | `logical_interface_{received,transmitted}_{bytes,packets}_total` | `show interfaces lo0`/`irb` |
| `lacp` | `lacp_member_mux_state`, `lacp_member_receive_state`, `lacp_member_distributing` | `show lacp interfaces` |
| `lldp` | `lldp_neighbors`, `lldp_neighbor_info` | `show lldp neighbors` |
| `vxlan` | `vxlan_remote_vteps`, `vxlan_remote_vtep_vnis`, `mac_table` | `show ethernet-switching vxlan-tunnel-end-point remote`, `table summary` |

The `optics` type now also exports `interface_optics_alarm{interface,alarm}`
from the same RPC as the optic values, so the transceivers are not polled twice.

An optional `junos` block in the module tunes these collectors:

```yml
  junos:
    rpc_timeout: 20                          # seconds per RPC, default 60
    keep_session: false                      # reuse the NETCONF session between scrapes (probe)
    exclusive_session: true                  # one session slot per switch across modules
    session_wait_seconds: 30                 # wait this long for the slot, else fail the scrape
    rpc_retry_seconds: 900                   # an RPC Junos rejected is not asked again for this long
    dns_ttl_seconds: 3600                    # reverse DNS of peers and neighbours, cached per device
    processes: [rpd, mgd, fxpc]              # always exported, default: common daemons
    process_top: 10                          # plus the N busiest processes
    extensive_interfaces: "[ex][et]-*"       # interface pattern for show interfaces extensive
    extensive_description: "^(Core|Server)"  # regex on the description, "" for all
    logical_interfaces: [lo0, irb]
    storage_mounts: "^(/|(/\\.mount)?(/var|/tmp|/config)?)$"
```

Scrape health for every module: `pyez_junos_netconf_connect_seconds`,
`pyez_junos_collector_duration_seconds{collector}` and
`pyez_junos_collector_failed{collector}`. A collector that raises an error
no longer fails the whole scrape; only its own metrics are missing. Errors
that mean the NETCONF session is gone still abort the scrape.

Device objects are cached per target and module, so one target can be
scraped with several modules. To protect the routing engine, modules with
`exclusive_session` (the default) share one session slot per switch: while
one of them is connected, the others wait up to `session_wait_seconds` and
then fail with `DeviceBusy` instead of opening a parallel session. The probe
module opts out and keeps one long lived session (`keep_session`), so a 15s
probe costs one small RPC instead of an SSH login and a new mgd process.

`--config` selects another config file, which allows a second exporter
instance next to the production one.

`--processes N` starts N worker processes behind the one port. A Python
process runs its collectors on one CPU core, however many threads it has;
with the control plane modules of several cores one process is not enough
and every other scrape waits behind them. Each target always lands in the
same worker (hash of the hostname), so the connection pool, the session slot
and a kept NETCONF session of a switch stay in one process. `/metrics` is
served by the main process from the counters of every worker. When a worker
dies the exporter exits and systemd restarts it. Use one process per CPU
core the exporter may have, for example `--processes 4`.

## Look for prometheus config

Example config for your prometheus can be found under `prometheus/*`.

## For Enthusiasts

You can also configure the metrics definitions.
If their are not enough Metrics.
Configure `config/metrics_definitions.yml` and add functions to junos_exporter if the ouput is non trivial.

Interfaces, environment, IGMP, BGP, OSPF, route tables and BFD are supported.
So only the Metrics Counter, Gauge and Info are implemented.
Feel free to add Pull Requests to extend the implementation.
