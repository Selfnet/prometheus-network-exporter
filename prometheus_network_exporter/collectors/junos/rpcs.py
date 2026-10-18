"""Every Junos RPC the routing collectors use, with the exact arguments.

:func:`fixture_name` gives every call a stable name that labels the status
metrics, such as ``pyez_junos_rpc_failed{rpc=...}``.
"""

from __future__ import annotations

from typing import Dict, Tuple

OSPF_PROTOCOLS = ("ospf", "ospf3")

RPCS: Dict[str, Tuple[str, dict]] = {
    "bgp_neighbor": ("get_bgp_neighbor_information", {}),
    "bgp_summary": ("get_bgp_summary_information", {}),
    "bgp_group": ("get_bgp_group_information", {}),
    "bfd_session": ("get_bfd_session_information", {"extensive": True}),
    "route_summary": ("get_route_summary_information", {}),
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


def route_table_args(table: str) -> dict:
    return {"table": table, "active_path": True}


def fixture_name(rpc: str, args: dict) -> str:
    """Logical name of an RPC call, used as the rpc label of the status metrics."""
    rpc = rpc.replace("-", "_")
    if rpc == ROUTE_TABLE_RPC:
        return "route_table_{}".format(args.get("table", "default"))
    for name, (spec_rpc, spec_args) in RPCS.items():
        if spec_rpc == rpc and spec_args == args:
            return name
    return rpc
