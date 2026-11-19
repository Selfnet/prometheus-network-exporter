import unittest
from unittest.mock import Mock

from lxml import etree
import yaml

from prometheus_network_exporter.collectors.junos.interface_addresses import InterfaceAddressCollector, address_info
from prometheus_network_exporter.collectors.junos.transceivers import TransceiverCollector
from prometheus_network_exporter.collectors.junos.links import LLDPCollector
from prometheus_network_exporter.collectors.junos.xmlutil import SchemaWatch
from prometheus_network_exporter.devices.junosdevice import SIMPLE_COLLECTORS
from prometheus_network_exporter.schema import Configuration


def xml(value):
    return etree.fromstring(value)


def collect(collector):
    return [sample for family in collector.collect() for sample in family.samples]


class InventoryTests(unittest.TestCase):
    def device(self, pic=True):
        hardware = xml("""<chassis-inventory xmlns="urn:test"><chassis><chassis-module><name>FPC 0</name>
          <chassis-sub-module><name>PIC 1</name><chassis-sub-sub-module><name>Xcvr 2</name>
          <part-number>NON-JNPR</part-number><serial-number>serial-1</serial-number>
          <description>QSFP-40G-LR4</description></chassis-sub-sub-module></chassis-sub-module>
          </chassis-module></chassis></chassis-inventory>""")
        details = xml("""<pic-detail><port-information><port><port-number>2</port-number>
          <sfp-vendor-name>Example</sfp-vendor-name><sfp-vendor-part-number>PART-40G</sfp-vendor-part-number>
          </port></port-information></pic-detail>""") if pic else None
        interfaces = xml(
            "<interface-information>"
            + "".join(
                f"<physical-interface><name>{name}</name></physical-interface>"
                for name in ["xe-0/1/2:0", "xe-0/1/2:1", "xe-0/1/2:2", "xe-0/1/2:3", "xe-0/1/3"]
            )
            + "</interface-information>"
        )
        replies = {
            "get_chassis_inventory": hardware,
            "get_pic_detail": details,
            "get_interface_information": interfaces,
        }
        device = Mock()
        device.rpc_reply.side_effect = lambda name, **args: replies[name]
        return device

    def test_one_module_shared_by_four_breakout_ports(self):
        device = self.device()
        values = collect(TransceiverCollector(device))
        info = [v for v in values if v.name == "pyez_junos_transceiver_info"]
        mappings = [v for v in values if v.name == "pyez_junos_interface_transceiver_info"]
        self.assertEqual(len(info), 1)
        self.assertEqual(info[0].labels["module"], "0/1/2")
        self.assertEqual(info[0].labels["manufacturer"], "Example")
        self.assertEqual(info[0].labels["part_number"], "PART-40G")
        self.assertEqual(info[0].labels["serial_number"], "serial-1")
        self.assertEqual(len(mappings), 4)
        self.assertEqual({v.labels["module"] for v in mappings}, {"0/1/2"})
        self.assertEqual(sum(c.args[0] == "get_pic_detail" for c in device.rpc_reply.call_args_list), 1)

    def test_pic_failure_preserves_chassis_inventory(self):
        values = collect(TransceiverCollector(self.device(pic=False)))
        info = next(v for v in values if v.name == "pyez_junos_transceiver_info")
        self.assertEqual(info.labels["manufacturer"], "")
        self.assertEqual(info.labels["part_number"], "NON-JNPR")

    def test_conflicting_inventory_skips_only_that_module(self):
        device = self.device(pic=False)
        hardware = xml("""<chassis-inventory><chassis><chassis-module><name>FPC 0</name>
          <chassis-sub-module><name>PIC 1</name>
          <chassis-sub-sub-module><name>Xcvr 2</name><serial-number>serial-1</serial-number></chassis-sub-sub-module>
          <chassis-sub-sub-module><name>Xcvr 2</name><serial-number>serial-2</serial-number></chassis-sub-sub-module>
          <chassis-sub-sub-module><name>Xcvr 3</name><serial-number>serial-3</serial-number></chassis-sub-sub-module>
          </chassis-sub-module></chassis-module></chassis></chassis-inventory>""")
        replies = {
            "get_chassis_inventory": hardware,
            "get_pic_detail": None,
            "get_interface_information": device.rpc_reply("get_interface_information"),
        }
        device.rpc_reply.side_effect = lambda name, **args: replies[name]
        values = collect(TransceiverCollector(device))
        info = [v for v in values if v.name == "pyez_junos_transceiver_info"]
        self.assertEqual([v.labels["module"] for v in info], ["0/1/3"])

    def test_rpc_failure_does_not_invent_empty_inventory(self):
        device = Mock()
        device.rpc_reply.return_value = None
        self.assertEqual(collect(TransceiverCollector(device)), [])


class AddressTests(unittest.TestCase):
    def test_prefixes_and_unknowns(self):
        self.assertEqual(address_info("192.0.2.1/31", None)["network"], "192.0.2.0/31")
        self.assertEqual(address_info("2001:db8::1/127", None)["prefix_length"], "127")
        self.assertEqual(address_info("192.0.2.1", "192.0.2/24")["network"], "192.0.2.0/24")
        self.assertEqual(address_info("192.0.2.1", "192.0.2.2")["prefix_length"], "")
        self.assertEqual(address_info("192.0.2.1", "198.51.100.0/24")["network"], "")
        self.assertEqual(address_info("192.0.2.1", "invalid/24")["network"], "")
        self.assertIsNone(address_info("invalid", None))

    def test_parent_mapping_dual_stack_and_duplicates(self):
        entry = """<interface-address><ifa-local>192.0.2.1/31</ifa-local></interface-address>"""
        device = Mock()
        device.rpc_reply.return_value = xml(
            """<interface-information xmlns="urn:test"><physical-interface>
          <name>xe-0/1/2:0</name><logical-interface><name>xe-0/1/2:0.0</name><address-family>
          <address-family-name>inet</address-family-name>"""
            + entry * 2
            + """</address-family>
          <address-family><address-family-name>inet6</address-family-name><interface-address>
          <ifa-local>2001:db8::1/127</ifa-local></interface-address></address-family>
          </logical-interface></physical-interface></interface-information>"""
        )
        values = collect(InterfaceAddressCollector(device))
        self.assertEqual(len(values), 2)
        self.assertEqual({v.labels["family"] for v in values}, {"inet", "inet6"})
        for value in values:
            self.assertEqual(value.labels["interface"], "xe-0/1/2:0.0")
            self.assertEqual(value.labels["parent_interface"], "xe-0/1/2:0")
            self.assertEqual(value.labels["routing_instance"], "")

    def test_internal_and_link_local_addresses_are_skipped(self):
        def unit(parent, name, address):
            return (
                f"<physical-interface><name>{parent}</name><logical-interface><name>{name}</name>"
                "<address-family><address-family-name>inet6</address-family-name><interface-address>"
                f"<ifa-local>{address}</ifa-local></interface-address></address-family>"
                "</logical-interface></physical-interface>"
            )

        device = Mock()
        device.rpc_reply.return_value = xml(
            "<interface-information>"
            + "".join(
                [
                    unit("xe-0/0/1", "xe-0/0/1.0", "fe80::1/64"),
                    unit("xe-0/0/1", "xe-0/0/1.0", "2001:db8::1/127"),
                    unit("lo0", "lo0.0", "2001:db8:ffff::1/128"),
                    unit("lo0", "lo0.0", "::1/128"),
                    unit("lo0", "lo0.16385", "2001:db8:ffff::2/128"),
                    unit("bme0", "bme0.0", "2001:db8:fffe::1/64"),
                ]
            )
            + "</interface-information>"
        )
        values = collect(InterfaceAddressCollector(device))
        self.assertEqual(sorted(v.labels["address"] for v in values), ["2001:db8::1", "2001:db8:ffff::1"])

    def test_rpc_failure(self):
        device = Mock()
        device.rpc_reply.return_value = None
        self.assertEqual(collect(InterfaceAddressCollector(device)), [])

    def test_missing_names_invalid_addresses_and_non_ip_families_are_skipped(self):
        device = Mock()
        device.rpc_reply.return_value = xml("""<interface-information>
          <physical-interface><logical-interface><name>ae0.0</name></logical-interface></physical-interface>
          <physical-interface><name>ae0</name><logical-interface><name>ae0.0</name>
            <address-family><address-family-name>mpls</address-family-name>
              <interface-address><ifa-local>192.0.2.99</ifa-local></interface-address></address-family>
            <address-family><address-family-name>inet</address-family-name>
              <interface-address/>
              <interface-address><ifa-local>invalid</ifa-local></interface-address>
              <interface-address><ifa-local>192.0.2.1/31</ifa-local></interface-address>
            </address-family>
          </logical-interface></physical-interface></interface-information>""")
        values = collect(InterfaceAddressCollector(device))
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0].labels["address"], "192.0.2.1")
        self.assertEqual(values[0].labels["network"], "192.0.2.0/31")


class LinkConfigurationTests(unittest.TestCase):
    def test_lldp_preserves_port_id_and_description_separately(self):
        device = Mock()
        device.schema = SchemaWatch()
        device.rpc_reply.return_value = xml("""<lldp-neighbors-information><lldp-neighbor-information>
          <lldp-local-port-id>xe-0/1/2:0</lldp-local-port-id><lldp-remote-chassis-id>00:00:5e:00:53:55</lldp-remote-chassis-id>
          <lldp-remote-system-name>peer-2</lldp-remote-system-name><lldp-remote-port-id>25GE1/0/1</lldp-remote-port-id>
          <lldp-remote-port-description>Core: peer-1</lldp-remote-port-description>
          </lldp-neighbor-information></lldp-neighbors-information>""")
        value = next(v for v in collect(LLDPCollector(device)) if v.name == "pyez_junos_lldp_neighbor_info")
        self.assertEqual(value.labels["remote_port_id"], "25GE1/0/1")
        self.assertEqual(value.labels["remote_port_description"], "Core: peer-1")
        self.assertEqual(value.labels["remote_port"], "Core: peer-1")

    def test_optional_modules_are_registered_and_config_validates(self):
        self.assertEqual(SIMPLE_COLLECTORS["transceivers"], (TransceiverCollector,))
        self.assertEqual(SIMPLE_COLLECTORS["interface_addresses"], (InterfaceAddressCollector,))
        with open("prometheus_network_exporter/config/config.yml") as file:
            config = yaml.safe_load(file)
        Configuration().schema(config)


if __name__ == "__main__":
    unittest.main()
