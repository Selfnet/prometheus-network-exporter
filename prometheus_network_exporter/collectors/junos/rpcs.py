"""Every Junos RPC the lxml based collectors use, with the exact arguments.

:func:`fixture_name` gives every call a stable name that labels the status
metrics, such as ``pyez_junos_rpc_failed{rpc=...}``.

Commands whose RPC name or XML schema could not be checked against a device
run through ``rpc.cli(command=..., format="xml")``. Junos translates the CLI
command itself, so a wrong RPC name cannot break them; a command without an
XML schema answers with an ``<output>`` text element, which the collectors
parse as text.
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

OSPF_PROTOCOLS = ("ospf", "ospf3")
CLI_RPC = "cli"

# Arguments that only narrow down which interfaces a reply covers. They do
# not change the reply schema and are left out of the fixture name.
FILTER_ARGS = ("interface", "interface_name")


def cli(command: str) -> Tuple[str, dict]:
    return (CLI_RPC, {"command": command, "format": "xml"})


RPCS: Dict[str, Tuple[str, dict]] = {
    # routing protocols
    "bgp_neighbor": ("get_bgp_neighbor_information", {}),
    "bgp_summary": ("get_bgp_summary_information", {}),
    "bgp_group": ("get_bgp_group_information", {}),
    "bfd_session": ("get_bfd_session_information", {"extensive": True}),
    "route_summary": ("get_route_summary_information", {}),
    "ldp_session": ("get_ldp_session_information", {"detail": True}),
    "ldp_neighbor": ("get_ldp_neighbor_information", {}),
    "l2circuit": ("get_l2ckt_connection_information", {}),
    "pim_neighbors": ("get_pim_neighbors_information", {}),
    "fib_summary": ("get_forwarding_table_information", {"summary": True}),
    "krt_queue": cli("show krt queue"),
    "krt_state": cli("show krt state"),
    "task_memory": cli("show task memory"),
    "arp_table": ("get_arp_table_information", {"no_resolve": True}),
    "nd_table": ("get_ipv6_nd_information", {}),
    # control plane
    "probe": ("get_software_information", {}),
    "route_engine": ("get_route_engine_information", {}),
    "processes": cli("show system processes extensive"),
    "fpc": ("get_fpc_information", {}),
    "chassis_alarms": ("get_alarm_information", {}),
    "system_alarms": ("get_system_alarm_information", {}),
    "core_dumps": cli("show system core-dumps"),
    "uptime": ("get_system_uptime_information", {}),
    "storage": ("get_system_storage", {}),
    "ntp_status": cli("show ntp status"),
    # forwarding plane
    "pfe_traffic": ("get_pfe_statistics", {}),
    "pfe_exceptions": cli("show pfe statistics exceptions"),
    "pfe_hw_routes": cli("show pfe route summary hw"),
    "ddos_statistics": cli("show ddos-protection protocols statistics terse"),
    "ddos_violations": cli("show ddos-protection protocols violations"),
    # interfaces and layer 2
    "interface_extensive": ("get_interface_information", {"extensive": True}),
    "interfaces_brief": ("get_interface_information", {}),
    "lacp": ("get_lacp_interface_information", {}),
    "lldp": ("get_lldp_neighbors_information", {}),
    "vxlan_remote_vteps": cli("show ethernet-switching vxlan-tunnel-end-point remote"),
    "mac_table_summary": cli("show ethernet-switching table summary"),
}
for _protocol in OSPF_PROTOCOLS:
    RPCS[f"{_protocol}_neighbor"] = (
        f"get_{_protocol}_neighbor_information",
        {"extensive": True},
    )
    RPCS[f"{_protocol}_interface"] = (
        f"get_{_protocol}_interface_information",
        {"detail": True},
    )
    RPCS[f"{_protocol}_overview"] = (f"get_{_protocol}_overview_information", {})
    RPCS[f"{_protocol}_database"] = (f"get_{_protocol}_database_information", {})
    RPCS[f"{_protocol}_route"] = (
        f"get_{_protocol}_route_information",
        {"detail": True},
    )
    RPCS[f"{_protocol}_statistics"] = (
        f"get_{_protocol}_statistics_information",
        {},
    )

ROUTE_TABLE_RPC = "get_route_information"
INTERFACE_RPC = "get_interface_information"
LOGICAL_INTERFACE_ARGS = {"statistics": True, "detail": True}


def route_table_args(table: str) -> dict:
    return {"table": table, "active_path": True}


def route_destination_args(prefix: str, table: str) -> dict:
    return {"destination": prefix, "table": table, "exact": True, "active_path": True}


def logical_interface_args(name: str) -> dict:
    return {**LOGICAL_INTERFACE_ARGS, "interface_name": name}


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "_", value).strip("_")


def _is_logical_interface_call(rpc: str, args: dict) -> bool:
    return (
        rpc == INTERFACE_RPC
        and "interface_name" in args
        and {k: v for k, v in args.items() if k != "interface_name"} == LOGICAL_INTERFACE_ARGS
    )


def fixture_name(rpc: str, args: dict) -> str:
    """Logical name of an RPC call, used as the rpc label of the status metrics."""
    rpc = rpc.replace("-", "_")
    if rpc == ROUTE_TABLE_RPC:
        if "destination" in args:
            prefix = args["destination"].replace(":", "x").replace("/", "_")
            return "route_destination_{}".format(_slug(prefix))
        return "route_table_{}".format(args.get("table", "default"))
    if _is_logical_interface_call(rpc, args):
        return "logical_interfaces_{}".format(_slug(args["interface_name"]))
    plain = {key: value for key, value in args.items() if key not in FILTER_ARGS}
    for name, (spec_rpc, spec_args) in RPCS.items():
        if spec_rpc == rpc and spec_args == plain:
            return name
    if rpc == CLI_RPC:
        return "cli_{}".format(_slug(args.get("command", "")))
    return rpc
