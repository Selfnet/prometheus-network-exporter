from voluptuous import Schema, Required, Optional, Any

import yaml


class Configuration(object):
    def __init__(self):
        self.schema = Schema(
            {
                Required(str): {
                    Required("device"): Any("junos", "arubaos", "ios", "airmax"),
                    Required("auth"): {
                        Required("method"): Any("password", "ssh_key"),
                        "username": str,
                        Any("password", "ssh_key", "proxy"): str,
                        "port": int,
                        Any("http_secure", "verify"): bool,
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
                        "vxlan",
                        # AirMax Metrics
                        "wireless statistics",
                        # ArubaOS Metrics
                        "clients",
                        "cpu",
                        "memory",
                        "system information",
                        "access point statistics",
                        "access point state",
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
                        # Reuse the NETCONF session between scrapes (probe module).
                        Optional("keep_session"): bool,
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
