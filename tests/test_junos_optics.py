import math
from pathlib import Path
import unittest
from unittest.mock import Mock

from lxml import etree
from prometheus_client import CollectorRegistry, generate_latest

from prometheus_network_exporter.devices.junosdevice import JuniperNetworkDevice
from prometheus_network_exporter.collectors.junos.optics import OpticsCollector, StandaloneOpticsCollector
from prometheus_network_exporter.collectors.junos.optics_xml import parse_optics

FIXTURE = Path(__file__).parent / "fixtures" / "junos" / "optics_breakout.xml"


def samples(collector, interfaces=None):
    result = {}
    generator = collector.collect(interfaces) if interfaces is not None else collector.collect()
    for family in generator:
        for sample in family.samples:
            key = (sample.name, tuple(sorted(sample.labels.items())))
            if key in result:
                raise AssertionError("Duplicate sample: " + str(key))
            result[key] = sample.value
    return result


def select(data, name, **labels):
    return [
        value
        for (metric, keys), value in data.items()
        if metric == name and all(dict(keys).get(k) == v for k, v in labels.items())
    ]


def reply(name, body):
    return etree.fromstring(
        f"<interface-information><physical-interface><name>{name}</name>"
        f"<optics-diagnostics>{body}</optics-diagnostics>"
        "</physical-interface></interface-information>"
    )


class OpticsTests(unittest.TestCase):
    def test_parser_skips_comments_and_ports_without_names_or_diagnostics(self):
        result = parse_optics(etree.fromstring("""<interface-information>
          <physical-interface><optics-diagnostics><module-temperature>90</module-temperature></optics-diagnostics></physical-interface>
          <physical-interface><name>et-0/0/1</name></physical-interface>
          <physical-interface><name>et-0/0/2</name><optics-diagnostics><!-- sensor -->
            <module-temperature celsius="42">42 degrees C</module-temperature>
            <laser-output-power-low-alarm>on</laser-output-power-low-alarm>
          </optics-diagnostics></physical-interface></interface-information>"""))
        self.assertEqual(set(result), {"et-0/0/2"})
        self.assertEqual(result["et-0/0/2"]["module_temperature"], 42)
        self.assertEqual(result["et-0/0/2"]["flag_laser_output_power_low_alarm"], "on")

    def test_standalone_collector_skips_an_interface_without_a_name(self):
        device = Mock(spec=JuniperNetworkDevice)
        device.rpc_reply.return_value = etree.fromstring("""<interface-information>
          <physical-interface><description>unnamed</description></physical-interface>
          <physical-interface><name>et-0/0/2</name><description>uplink</description></physical-interface>
          </interface-information>""")
        device.get_optics.return_value = {"et-0/0/2": {"module_temperature": 42}}
        data = samples(StandaloneOpticsCollector(device))
        self.assertEqual(
            select(data, "pyez_junos_interface_temperature_celsius", interface="et-0/0/2", description="uplink"), [42]
        )
        self.assertEqual(len(data), 1)

    def collector(self, values):
        device = Mock(spec=JuniperNetworkDevice)
        device.get_optics.return_value = values
        interfaces = {name: {"description": "Core: peer", "macaddr": "", "speed": "100Gbps"} for name in values}
        return OpticsCollector(device), interfaces

    def test_breakout_values_and_missing_diagnostics(self):
        values = parse_optics(etree.parse(str(FIXTURE)).getroot())
        collector, interfaces = self.collector(values)
        data = samples(collector, interfaces)
        for lane, rx in [("0", -5.0), ("1", -4.0), ("2", -3.0), ("3", -2.0)]:
            interface = "xe-0/1/1:" + lane
            self.assertEqual(
                select(data, "pyez_junos_interface_lane_receiving_optic_power_dbm", interface=interface, lane=lane),
                [rx],
            )
            self.assertEqual(select(data, "pyez_junos_interface_receiving_optic_power_dbm", interface=interface), [rx])
            self.assertEqual(
                select(
                    data,
                    "pyez_junos_interface_lane_receiving_optic_power_low_alarm_threshold_dbm",
                    interface=interface,
                    lane=lane,
                ),
                [-14.0],
            )
        self.assertEqual(select(data, "pyez_junos_interface_receiving_optic_power_dbm", interface="xe-0/1/0:0"), [])
        self.assertEqual(select(data, "pyez_junos_interface_optics_available", interface="xe-0/1/0:0"), [0])
        self.assertEqual(select(data, "pyez_junos_interface_voltage_volts", interface="xe-0/1/1:0"), [3.3])
        collector.device.get_optics.assert_called_once_with()

    def test_multiple_lanes_no_average_or_speed_based_count(self):
        xml = reply(
            "et-0/0/0",
            """<laser-rx-power-low-alarm-threshold-dbm>-14</laser-rx-power-low-alarm-threshold-dbm>
          <optics-diagnostics-lane-values><lane-index>2</lane-index>
            <laser-rx-optical-power-dbm>-4</laser-rx-optical-power-dbm>
            <laser-output-power-dbm>0</laser-output-power-dbm></optics-diagnostics-lane-values>
          <optics-diagnostics-lane-values><lane-index>7</lane-index>
            <laser-rx-optical-power-dbm>- Inf</laser-rx-optical-power-dbm>
            <laser-rx-power-low-alarm-threshold-dbm>-18</laser-rx-power-low-alarm-threshold-dbm>
            <rx-loss-of-signal-alarm>on</rx-loss-of-signal-alarm></optics-diagnostics-lane-values>""",
        )
        values = parse_optics(xml)
        collector, interfaces = self.collector(values)
        data = samples(collector, interfaces)
        self.assertEqual(select(data, "pyez_junos_interface_optics_reported_lanes"), [2])
        self.assertEqual(select(data, "pyez_junos_interface_receiving_optic_power_dbm"), [])
        self.assertEqual(
            select(data, "pyez_junos_interface_lane_receiving_optic_power_low_alarm_threshold_dbm", lane="7"), [-18]
        )
        self.assertEqual(
            select(data, "pyez_junos_interface_lane_receiving_optic_power_low_alarm_threshold_dbm", lane="2"), [-14]
        )
        self.assertEqual(select(data, "pyez_junos_interface_lane_sending_optic_power_dbm", lane="2"), [0])
        self.assertEqual(select(data, "pyez_junos_interface_lane_receiving_optic_power_dbm", lane="7"), [-math.inf])
        self.assertEqual(
            select(data, "pyez_junos_interface_lane_optics_alarm", lane="7", alarm="rx_loss_of_signal_alarm"), [1]
        )

    def test_single_reported_lane_and_scalar_diagnostics(self):
        xml = reply(
            "et-0/0/0",
            """<optics-diagnostics-lane-values><lane-index>0</lane-index>
           <laser-rx-optical-power-dbm>0</laser-rx-optical-power-dbm></optics-diagnostics-lane-values>""",
        )
        collector, interfaces = self.collector(parse_optics(xml))
        data = samples(collector, interfaces)
        self.assertEqual(select(data, "pyez_junos_interface_optics_reported_lanes"), [1])
        self.assertEqual(select(data, "pyez_junos_interface_receiving_optic_power_dbm"), [0])
        scalar = parse_optics(reply("et-0/0/1", "<laser-output-power-dbm>0</laser-output-power-dbm>"))
        collector, interfaces = self.collector(scalar)
        data = samples(collector, interfaces)
        self.assertEqual(select(data, "pyez_junos_interface_optics_reported_lanes"), [])
        self.assertEqual(select(data, "pyez_junos_interface_sending_optic_power_dbm"), [0])
        self.assertEqual(select(data, "pyez_junos_interface_receiving_optic_power_dbm"), [])

    def test_lane_bias_metrics_only_in_milliamps(self):
        xml = reply(
            "et-0/0/0",
            """<laser-bias-current-high-alarm-threshold>75</laser-bias-current-high-alarm-threshold>
          <optics-diagnostics-lane-values><lane-index>0</lane-index>
            <laser-bias-current>35.9</laser-bias-current></optics-diagnostics-lane-values>
          <optics-diagnostics-lane-values><lane-index>1</lane-index>
            <laser-bias-current>36.1</laser-bias-current></optics-diagnostics-lane-values>""",
        )
        collector, interfaces = self.collector(parse_optics(xml))
        data = samples(collector, interfaces)
        lane_metrics = {metric for metric, _ in data if metric.startswith("pyez_junos_interface_lane_laser_bias")}
        self.assertTrue(lane_metrics)
        self.assertFalse([metric for metric in lane_metrics if metric.endswith("_dbm")])
        self.assertEqual(sorted(select(data, "pyez_junos_interface_lane_laser_bias_current_milliamps")), [35.9, 36.1])
        self.assertEqual(select(data, "pyez_junos_interface_lane_laser_bias_high_alarm_threshold_milliamps"), [75, 75])

    def test_ambiguous_breakout_is_not_promoted(self):
        values = parse_optics(
            reply(
                "xe-0/0/0:3",
                """<optics-diagnostics-lane-values><lane-index>0</lane-index>
           <laser-rx-optical-power-dbm>-5</laser-rx-optical-power-dbm></optics-diagnostics-lane-values>""",
            )
        )
        self.assertNotIn("rx_optic_power", values["xe-0/0/0:3"])
        self.assertEqual(values["xe-0/0/0:3"]["lanes"]["0"]["rx_optic_power"], -5)

    def test_single_lane_threshold_overrides_common_threshold(self):
        values = parse_optics(
            reply(
                "xe-0/1/1:2",
                """
          <laser-rx-power-low-alarm-threshold-dbm>-14</laser-rx-power-low-alarm-threshold-dbm>
          <optics-diagnostics-lane-values><lane-index>2</lane-index>
          <laser-rx-power-low-alarm-threshold-dbm>-18</laser-rx-power-low-alarm-threshold-dbm>
          </optics-diagnostics-lane-values>""",
            )
        )
        collector, interfaces = self.collector(values)
        data = samples(collector, interfaces)
        self.assertEqual(select(data, "pyez_junos_interface_receiving_optic_power_low_alarm_threshold"), [-18])
        self.assertEqual(select(data, "pyez_junos_interface_lane_receiving_optic_power_low_alarm_threshold_dbm"), [-18])
        lane_names = {metric for metric, _ in data if "_lane_" in metric and "optic_power" in metric}
        self.assertTrue(all(name.endswith("_dbm") for name in lane_names), lane_names)

    def test_device_uses_one_rpc_for_all_reported_lanes(self):
        device = Mock(spec=JuniperNetworkDevice)
        device.rpc_reply.return_value = etree.parse(str(FIXTURE)).getroot()
        values = JuniperNetworkDevice.get_optics(device)
        self.assertEqual(values["xe-0/1/1:2"]["lanes"]["2"]["rx_optic_power"], -3.0)
        device.rpc_reply.assert_called_once_with(
            "get_interface_optics_diagnostics_information", interface_name="[efgx][et]-*"
        )

    def test_duplicate_or_missing_lane_ids_are_skipped_not_overwritten(self):
        lane = (
            "<optics-diagnostics-lane-values><lane-index>0</lane-index>"
            "<laser-rx-optical-power-dbm>{}</laser-rx-optical-power-dbm></optics-diagnostics-lane-values>"
        )
        body = (
            "<optics-diagnostics-lane-values><laser-rx-optical-power-dbm>-9</laser-rx-optical-power-dbm>"
            "</optics-diagnostics-lane-values>" + lane.format(-4) + lane.format(-7)
        )
        with self.assertLogs("network_exporter", level="WARNING") as logs:
            values = parse_optics(reply("et-0/0/0", body))["et-0/0/0"]
        self.assertEqual(len(logs.records), 2)
        self.assertEqual(list(values["lanes"]), ["0"])
        self.assertEqual(values["lanes"]["0"]["rx_optic_power"], -4)

    def test_namespace_and_invalid_numeric_values(self):
        xml = reply(
            "xe-0/0/0",
            "<laser-output-power-dbm>NaN</laser-output-power-dbm>"
            "<laser-rx-optical-power-dbm>N/A</laser-rx-optical-power-dbm>"
            "<tx-laser-fault-alarm>off</tx-laser-fault-alarm>",
        )
        self.assertEqual(parse_optics(xml)["xe-0/0/0"]["tx_laser_fault_alarm"], True)
        self.assertNotIn("tx_optic_power", parse_optics(xml)["xe-0/0/0"])
        for e in xml.iter():
            e.tag = "{urn:test}" + e.tag
        self.assertEqual(parse_optics(xml)["xe-0/0/0"]["diagnostics_available"], 1)

    def test_standalone_collector_and_repeated_scrapes(self):
        device = Mock(spec=JuniperNetworkDevice)
        values = parse_optics(etree.parse(str(FIXTURE)).getroot())
        device.get_optics.return_value = values
        device.rpc_reply.return_value = etree.fromstring(
            "<interface-information>"
            + "".join(f"<physical-interface><name>{name}</name></physical-interface>" for name in values)
            + "</interface-information>"
        )
        collector = StandaloneOpticsCollector(device)
        registry = CollectorRegistry(auto_describe=False)
        registry.register(collector)
        first = generate_latest(registry)
        second = generate_latest(registry)
        self.assertEqual(first, second)
        self.assertIn(b"pyez_junos_interface_lane_receiving_optic_power_dbm", first)
        device.get_optics.return_value = {}
        self.assertNotIn(b"pyez_junos_interface_lane_receiving_optic_power_dbm{", generate_latest(registry))


if __name__ == "__main__":
    unittest.main()
