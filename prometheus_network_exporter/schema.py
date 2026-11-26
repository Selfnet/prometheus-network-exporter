from voluptuous import Schema, Required, Optional, Any, All, Range

import yaml


class Configuration(object):
    def __init__(self):
        self.schema = Schema(
            {
                Required(str): {
                    Required("device"): "junos",
                    Required("auth"): {
                        Required("method"): Any("password", "ssh_key"),
                        Optional("username"): str,
                        Optional("password"): str,
                        Optional("ssh_key"): str,
                        Optional("ssh_config"): str,
                        Optional("port"): int,
                    },
                    Required("metrics"): [
                        # Junos Metrics
                        "ospf",
                        "optics",
                        "interface",
                        "interface_specifics",
                        "igmp",
                        "environment",
                        "bgp",
                        "bgp_details",
                        "ospf_details",
                        "routes",
                        "bfd",
                        "route_watch",
                        "probe",
                        "routing_engine",
                        "processes",
                        "fpc",
                        "alarms",
                        "core_dumps",
                        "system",
                        "pfe",
                        "pfe_exceptions",
                        "pfe_hw_tables",
                        "ddos",
                        "krt",
                        "rpd_memory",
                        "fib",
                        "ldp",
                        "l2circuit",
                        "pim",
                        "neighbor_tables",
                        "interface_errors",
                        "logical_interfaces",
                        "lacp",
                        "lldp",
                        "transceivers",
                        "interface_addresses",
                        "vxlan",
                    ],
                    # Junos only: route tables to dump, prefixes to watch and
                    # the age below which a route counts as young.
                    Optional("routing"): {
                        Optional("tables"): [str],
                        Optional("watch"): [str],
                        Optional("young_route_seconds"): int,
                    },
                    # Junos only: knobs of the control plane and interface collectors.
                    Optional("junos"): {
                        Optional("rpc_timeout"): int,
                        Optional("optics_interval_seconds"): All(int, Range(min=0)),
                        # Reuse the NETCONF session between scrapes (probe module).
                        Optional("keep_session"): bool,
                        # SSH keepalive of a kept session in seconds, 0 for none.
                        Optional("keepalive_seconds"): All(int, Range(min=0)),
                        # Share one session slot per switch with the other modules.
                        Optional("exclusive_session"): bool,
                        Optional("session_wait_seconds"): int,
                        # Seconds an RPC Junos rejected is not asked again.
                        Optional("rpc_retry_seconds"): int,
                        # Reverse DNS of peers and neighbours is cached this long.
                        Optional("dns_ttl_seconds"): int,
                        Optional("processes"): [str],
                        Optional("process_top"): int,
                        Optional("extensive_interfaces"): str,
                        # Empty string: every interface the RPC returns.
                        Optional("extensive_description"): str,
                        Optional("logical_interfaces"): [str],
                        # Regex on the description: interface, optics, transceivers and
                        # interface_addresses export only matching interfaces; unset for all.
                        Optional("interface_description"): str,
                        Optional("storage_mounts"): str,
                    },
                }
            }
        )

    def validate(self, config):
        self.schema(config)


if __name__ == "__main__":
    import sys

    config = Configuration()
    path = sys.argv[1] if len(sys.argv) > 1 else "prometheus_network_exporter/config/config.yml"
    with open(path, "r") as file:
        data = yaml.safe_load(file)
    config.validate(data)
