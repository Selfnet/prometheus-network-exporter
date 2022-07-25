from voluptuous import Schema, Required, Any

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
                        Any("password", "ssh_key", "proxy", "ssh_config"): str,
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
                }
            }
        )

    def validate(self, config):
        self.schema(config)


if __name__ == "__main__":
    config = Configuration()
    with open("prometheus_network_exporter/config/config.yml", "r") as file:
        data = yaml.safe_load(file)
    config.validate(data)
