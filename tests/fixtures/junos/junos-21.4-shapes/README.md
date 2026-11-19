# Junos 21.4 reply shapes

Hand-written replies in the layout Junos 21.4 uses on EX4600, with
documentation values (RFC 5737, RFC 3849, RFC 5398). They pin the layouts
that differed from the first assumptions:

- `bgp_group`: the element is `type`, and one configured group appears several
  times (one entry per option set).
- `ddos_*`: `group-name` and `packet-type` sit inside `ddos-system-statistics`;
  violations are counted in `packet-types-in-violation`.
- `fib_summary`: empty `route-table` separators and bridge domain tables that
  share a `table-name` but carry `bd-name`.
- `pim_neighbors`: the interface name is inside each `pim-neighbor`.
- `ntp_status`: ntpd on the switch did not answer the local query.
- `krt_state`: the queue counters are nested in `krt-queue-state`.
- `vxlan_remote_vteps`: a switch with its own VTEP but no remote ones.
- `ospf_interface`: a loopback with two addresses is listed once per address.
