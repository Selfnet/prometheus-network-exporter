"""Option interface_description: only interfaces with a matching description are exported."""

import shutil
from unittest.mock import Mock

from lxml import etree

from prometheus_network_exporter.collectors.junos.interface_addresses import InterfaceAddressCollector
from prometheus_network_exporter.collectors.junos.interface_filter import DescriptionFilter
from prometheus_network_exporter.collectors.junos.transceivers import TransceiverCollector
from prometheus_network_exporter.schema import Configuration

from .conftest import SYNTHETIC, make_device, samples, scrape

LEGACY = ("logical_interfaces_afgxe_et", "optics", "ospf_neighbor", "ospf3_neighbor", "interfaces_brief")


def copy_fixtures(tmp_path, names=LEGACY):
    for name in names:
        shutil.copy(SYNTHETIC / f"{name}.xml", tmp_path / f"{name}.xml")
    return tmp_path


def interfaces(found, name):
    return {labels["interface"] for labels, _ in found.get(name, [])}


def xml(value):
    return etree.fromstring(value)


def descriptions_reply(entries):
    return xml(
        "<interface-information>"
        + "".join(
            f"<physical-interface><name>{name}</name><description>{description}</description>"
            f"<logical-interface><name>{name}.0</name><description>unit</description></logical-interface>"
            "</physical-interface>"
            for name, description in entries.items()
        )
        + "</interface-information>"
    )


def collect(collector):
    return [sample for family in collector.collect() for sample in family.samples]


def test_without_the_option_every_interface_is_exported(tmp_path):
    device = make_device(copy_fixtures(tmp_path), types=["interface", "ospf", "optics"])
    found = samples(scrape(device))
    assert interfaces(found, "pyez_junos_interface_is_operational") == {
        "xe-0/2/0",
        "et-0/0/26",
        "xe-0/0/16",
        "ae0",
        "irb",
    }
    assert "irb" in interfaces(found, "pyez_junos_interface_ospf_neighbor_state")


def test_interface_ospf_and_optics_follow_the_description(tmp_path):
    device = make_device(
        copy_fixtures(tmp_path),
        types=["interface", "ospf", "optics"],
        options={"interface_description": "^Core: "},
    )
    found = samples(scrape(device))
    assert interfaces(found, "pyez_junos_interface_is_operational") == {"xe-0/2/0", "et-0/0/26", "ae0"}
    assert interfaces(found, "pyez_junos_interface_received_bytes_total") == {"xe-0/2/0", "et-0/0/26", "ae0"}
    # The neighbours on irb.100 belong to an interface without a Core description.
    assert interfaces(found, "pyez_junos_interface_ospf_neighbor_state") == {"ae0"}
    assert interfaces(found, "pyez_junos_interface_ospf3_neighbor_state") == {"ae0"}
    assert interfaces(found, "pyez_junos_interface_receiving_optic_power_dbm") == {"xe-0/2/0"}
    # The interface collector filters on the descriptions it already has.
    assert "interface_descriptions" not in device.device.rpc.calls


def test_ports_outside_the_pattern_lose_their_optics_too(tmp_path):
    device = make_device(
        copy_fixtures(tmp_path), types=["interface", "optics"], options={"interface_description": "^Server: "}
    )
    found = samples(scrape(device))
    assert interfaces(found, "pyez_junos_interface_is_operational") == {"xe-0/0/16"}
    assert not interfaces(found, "pyez_junos_interface_receiving_optic_power_dbm")
    assert not interfaces(found, "pyez_junos_interface_optics_alarm")
    assert not interfaces(found, "pyez_junos_interface_optics_available")


def test_standalone_optics_follow_the_description(tmp_path):
    copy_fixtures(tmp_path)
    kept = samples(scrape(make_device(tmp_path, types=["optics"], options={"interface_description": "^Core: "})))
    assert interfaces(kept, "pyez_junos_interface_receiving_optic_power_dbm") == {"xe-0/2/0"}
    dropped = samples(scrape(make_device(tmp_path, types=["optics"], options={"interface_description": "^Member: "})))
    assert not interfaces(dropped, "pyez_junos_interface_receiving_optic_power_dbm")
    assert not interfaces(dropped, "pyez_junos_interface_optics_alarm")


class Replies:
    """rpc_reply of a mocked device; get_interface_information by its arguments."""

    def __init__(self, replies, descriptions=None):
        self.replies = replies
        self.descriptions = descriptions
        self.calls = []

    def __call__(self, name, **args):
        self.calls.append((name, tuple(sorted(args))))
        if name == "get_interface_information" and args.get("descriptions"):
            return self.descriptions
        return self.replies[name]


def transceiver_device(descriptions):
    hardware = xml("""<chassis-inventory><chassis><chassis-module><name>FPC 0</name>
      <chassis-sub-module><name>PIC 1</name>
      <chassis-sub-sub-module><name>Xcvr 2</name><serial-number>serial-2</serial-number>
      <description>SFP+-10G-LR</description></chassis-sub-sub-module>
      <chassis-sub-sub-module><name>Xcvr 3</name><serial-number>serial-3</serial-number>
      <description>SFP+-10G-SR</description></chassis-sub-sub-module>
      </chassis-sub-module></chassis-module></chassis></chassis-inventory>""")
    brief = xml(
        "<interface-information>"
        + "".join(f"<physical-interface><name>{name}</name></physical-interface>" for name in ("xe-0/1/2", "xe-0/1/3"))
        + "</interface-information>"
    )
    device = Mock()
    device.hostname = "switch.example.com"
    replies = Replies(
        {"get_chassis_inventory": hardware, "get_pic_detail": None, "get_interface_information": brief},
        descriptions,
    )
    device.rpc_reply.side_effect = replies
    return device, replies


def test_transceivers_only_of_matching_ports():
    device, replies = transceiver_device(descriptions_reply({"xe-0/1/2": "Core: core-a", "xe-0/1/3": "Member: 1"}))
    values = collect(TransceiverCollector(device, description_filter=DescriptionFilter("^Core: ")))
    assert [v.labels["module"] for v in values if v.name == "pyez_junos_transceiver_info"] == ["0/1/2"]
    assert [v.labels["interface"] for v in values if v.name == "pyez_junos_interface_transceiver_info"] == ["xe-0/1/2"]
    # The PIC detail is asked once, for the PIC of the remaining module.
    assert [call for call in replies.calls if call[0] == "get_pic_detail"] == [
        ("get_pic_detail", ("fpc_slot", "pic_slot"))
    ]


def test_transceivers_without_the_option_ask_for_no_descriptions():
    device, replies = transceiver_device(None)
    values = collect(TransceiverCollector(device))
    assert sorted(v.labels["module"] for v in values if v.name == "pyez_junos_transceiver_info") == ["0/1/2", "0/1/3"]
    assert ("get_interface_information", ("descriptions",)) not in replies.calls


def address_device(descriptions):
    units = {
        "xe-0/0/1": "192.0.2.0/31",
        "mge-0/0/9": "198.51.100.1/30",
        "irb": "203.0.113.1/24",
        "lo0": "192.0.2.255/32",
        "em0": "192.0.2.128/25",
    }
    terse = xml(
        "<interface-information>"
        + "".join(
            f"<physical-interface><name>{parent}</name><logical-interface><name>{parent}.0</name>"
            "<address-family><address-family-name>inet</address-family-name><interface-address>"
            f"<ifa-local>{address}</ifa-local></interface-address></address-family>"
            "</logical-interface></physical-interface>"
            for parent, address in units.items()
        )
        + "</interface-information>"
    )
    device = Mock()
    replies = Replies({"get_interface_information": terse}, descriptions)
    device.rpc_reply.side_effect = replies
    return device, replies


def parents(values):
    return {v.labels["parent_interface"] for v in values}


def test_addresses_only_on_matching_ports_and_the_switch_itself():
    device, _ = address_device(
        descriptions_reply({"xe-0/0/1": "Core: core-a", "mge-0/0/9": "Member: room 1", "em0": "management"})
    )
    values = collect(InterfaceAddressCollector(device, description_filter=DescriptionFilter("^(Core|WIFI-AP): ")))
    # irb carries the gateways of the members' networks; loopback and
    # management addresses belong to the switch.
    assert parents(values) == {"xe-0/0/1", "lo0", "em0"}


def test_addresses_fail_closed_without_descriptions():
    device, _ = address_device(None)
    values = collect(InterfaceAddressCollector(device, description_filter=DescriptionFilter("^Core: ")))
    assert parents(values) == {"lo0", "em0"}


def test_addresses_without_the_option_ask_for_no_descriptions():
    device, replies = address_device(None)
    values = collect(InterfaceAddressCollector(device))
    assert parents(values) == {"xe-0/0/1", "mge-0/0/9", "irb", "lo0", "em0"}
    assert ("get_interface_information", ("descriptions",)) not in replies.calls


def test_empty_pattern_filters_nothing():
    assert not DescriptionFilter("")
    assert DescriptionFilter("").allows(None)
    assert DescriptionFilter("^Core: ").allows("Core: x")
    assert not DescriptionFilter("^Core: ").allows(None)


def test_schema_accepts_the_option():
    Configuration().validate(
        {
            "access": {
                "device": "junos",
                "auth": {"method": "ssh_key", "username": "pyez"},
                "metrics": ["interface", "optics", "transceivers", "interface_addresses"],
                "junos": {"interface_description": "^(Core|WIFI-AP): "},
            }
        }
    )


def test_device_passes_the_filter_to_its_collectors(tmp_path):
    copy_fixtures(tmp_path)
    shutil.copy(SYNTHETIC / "interfaces_brief.xml", tmp_path / "interface_descriptions.xml")
    (tmp_path / "transceivers.xml").write_text("""<chassis-inventory><chassis><chassis-module>
      <name>FPC 0</name><chassis-sub-module><name>PIC 2</name><chassis-sub-sub-module><name>Xcvr 0</name>
      <serial-number>serial-0</serial-number></chassis-sub-sub-module></chassis-sub-module>
      </chassis-module></chassis></chassis-inventory>""")
    (tmp_path / "interface_addresses.xml").write_text("""<interface-information>
      <physical-interface><name>xe-0/2/0</name><logical-interface><name>xe-0/2/0.0</name>
      <address-family><address-family-name>inet</address-family-name><interface-address>
      <ifa-local>192.0.2.0/31</ifa-local></interface-address></address-family></logical-interface>
      </physical-interface>
      <physical-interface><name>xe-0/0/16</name><logical-interface><name>xe-0/0/16.0</name>
      <address-family><address-family-name>inet</address-family-name><interface-address>
      <ifa-local>198.51.100.1/30</ifa-local></interface-address></address-family></logical-interface>
      </physical-interface></interface-information>""")
    device = make_device(
        tmp_path,
        types=["interface", "transceivers", "interface_addresses"],
        options={"interface_description": "^Core: "},
    )
    found = samples(scrape(device))
    assert {labels["parent_interface"] for labels, _ in found["pyez_junos_interface_address_info"]} == {"xe-0/2/0"}
    assert [labels["module"] for labels, _ in found["pyez_junos_transceiver_info"]] == ["0/2/0"]
    # transceivers and interface_addresses share one descriptions RPC.
    assert device.device.rpc.calls.count("interface_descriptions") == 1
