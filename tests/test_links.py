"""Interface error and queue counters, logical units, LACP, LLDP, VXLAN, optics flags."""

import pytest

from prometheus_network_exporter.collectors.junos.optics import OpticsCollector

from .conftest import CONTROL_PLANE_TYPES, SYNTHETIC, labels_of, make_device, samples, scrape, value


@pytest.fixture
def found():
    return samples(scrape(make_device(SYNTHETIC, types=CONTROL_PLANE_TYPES)))


def test_interface_errors_only_for_matching_descriptions(found):
    name = "pyez_junos_interface_errors_total"
    interfaces = {labels["interface"] for labels, _ in found[name]}
    assert interfaces == {"et-0/0/26", "xe-0/0/16"}
    assert value(found, name, interface="et-0/0/26", list="output", counter="carrier_transitions") == 4
    assert value(found, name, interface="et-0/0/26", list="output", counter="mtu_errors") == 2
    assert value(found, name, interface="xe-0/0/16", list="mac", counter="input_crc_errors") == 12
    # Plain traffic counters of the MAC statistics are not error counters.
    assert not [labels for labels, _ in found[name] if labels["counter"] in ("input_unicasts", "input_bytes")]


def test_interface_errors_without_description_filter(tmp_path):
    (tmp_path / "interface_extensive.xml").write_text((SYNTHETIC / "interface_extensive.xml").read_text())
    device = make_device(tmp_path, types=["interface_errors"], options={"extensive_description": ""})
    result = samples(scrape(device))
    interfaces = {labels["interface"] for labels, _ in result["pyez_junos_interface_errors_total"]}
    assert "xe-0/0/23" in interfaces


def test_queue_counters(found):
    name = "pyez_junos_interface_queue_packets_total"
    assert value(found, name, interface="xe-0/0/16", queue="0", kind="tail_drop") == 1000
    assert value(found, name, interface="xe-0/0/16", queue="7", kind="trans") == 5000
    assert (
        labels_of(found, name, interface="et-0/0/26", queue="7", kind="queued")["forwarding_class"] == "network-control"
    )
    # Byte counters are left out.
    assert not [labels for labels, _ in found[name] if "bytes" in labels["kind"]]


def test_logical_interfaces(found):
    assert value(found, "pyez_junos_logical_interface_received_bytes_total", interface="lo0.0") == 5000000
    assert value(found, "pyez_junos_logical_interface_transmitted_packets_total", interface="irb.2102") == 80
    assert (
        labels_of(found, "pyez_junos_logical_interface_received_packets_total", interface="irb.2102")["description"]
        == "ceph"
    )


def test_lacp(found):
    assert value(found, "pyez_junos_lacp_member_distributing", lag="ae0", interface="xe-0/0/0") == 1
    assert value(found, "pyez_junos_lacp_member_distributing", lag="ae0", interface="xe-0/0/1") == 0
    assert value(found, "pyez_junos_lacp_member_receive_state", interface="xe-0/0/1", state="Defaulted") == 1
    assert value(found, "pyez_junos_lacp_member_mux_state", interface="xe-0/0/1", state="Attached") == 1


def test_lldp(found):
    assert value(found, "pyez_junos_lldp_neighbors") == 2
    info = labels_of(found, "pyez_junos_lldp_neighbor_info", interface="et-0/0/26")
    assert info["remote_system"] == "core-1"
    assert info["remote_port"] == "et-0/0/48"
    assert labels_of(found, "pyez_junos_lldp_neighbor_info", interface="xe-0/0/16")["remote_port"] == "enp3s0f1"


def test_vxlan(found):
    assert value(found, "pyez_junos_vxlan_remote_vteps") == 2
    assert value(found, "pyez_junos_vxlan_remote_vtep_vnis", vtep="192.0.2.105") == 2
    assert value(found, "pyez_junos_mac_table", vlan="", field="entries") == 1234
    assert value(found, "pyez_junos_mac_table", vlan="", field="learned") == 1200


def test_optics_alarm_flags():
    collector = OpticsCollector.__new__(OpticsCollector)
    collector.base_name = "pyez_junos_interface"
    family = collector.alarm_flags(
        [
            {
                "interface_name": "xe-0/2/0",
                "flag_laser_rx_power_low_alarm": "on",
                "flag_laser_bias_current_low_warn": "off",
                "flag_module_voltage_high_alarm": None,
                "rx_optic_power": "-30.0",
            }
        ]
    )
    flags = {sample.labels["alarm"]: sample.value for sample in family.samples}
    assert flags == {"laser_rx_power_low_alarm": 1.0, "laser_bias_current_low_warn": 0.0}


def test_vxlan_text_table(tmp_path):
    (tmp_path / "vxlan_remote_vteps.xml").write_text(
        "<rpc-reply><output>\n"
        "Logical System Name       Id  SVTEP-IP         IFL   L3-Idx    SVTEP-Mode\n"
        "&lt;default&gt;                 0   192.0.2.117     lo0.0    0\n"
        " RVTEP-IP         IFL-Idx   Interface    NH-Id   RVTEP-Mode\n"
        " 192.0.2.105      585       vtep.32769   1745    RNVE\n"
        "    VNID          MC-Group-IP\n"
        "    2000          0.0.0.0\n"
        "    2100          0.0.0.0\n"
        " RVTEP-IP         IFL-Idx   Interface    NH-Id   RVTEP-Mode\n"
        " 192.0.2.109      586       vtep.32770   1746    RNVE\n"
        "    VNID          MC-Group-IP\n"
        "    2000          0.0.0.0\n"
        "</output></rpc-reply>"
    )
    device = make_device(tmp_path, types=["vxlan"])
    found = samples(scrape(device))
    assert value(found, "pyez_junos_vxlan_remote_vteps") == 2
    assert value(found, "pyez_junos_vxlan_remote_vtep_vnis", vtep="192.0.2.105") == 2
    assert value(found, "pyez_junos_vxlan_remote_vtep_vnis", vtep="192.0.2.109") == 1


def test_vxlan_unparsable_is_not_zero(tmp_path):
    (tmp_path / "vxlan_remote_vteps.xml").write_text("<rpc-reply><output>something vtep else</output></rpc-reply>")
    device = make_device(tmp_path, types=["vxlan"])
    found = samples(scrape(device))
    assert "pyez_junos_vxlan_remote_vteps" not in found
    assert ("vxlan", "remote-vtep-address") in device.schema.missing


def test_lldp_two_neighbors_on_one_port(tmp_path):
    entry = (
        "<lldp-neighbor-information><lldp-local-port-id>xe-0/0/16</lldp-local-port-id>"
        "<lldp-remote-chassis-id>{}</lldp-remote-chassis-id>"
        "<lldp-remote-system-name>{}</lldp-remote-system-name></lldp-neighbor-information>"
    )
    (tmp_path / "lldp.xml").write_text(
        "<rpc-reply><lldp-neighbors-information>"
        + entry.format("00:00:5e:00:53:55", "server-1")
        + entry.format("00:00:5e:00:53:56", "server-1-bmc")
        + "</lldp-neighbors-information></rpc-reply>"
    )
    found = samples(scrape(make_device(tmp_path, types=["lldp"])))
    assert len(found["pyez_junos_lldp_neighbor_info"]) == 2


def test_optics_without_interface_collector():
    device = make_device(SYNTHETIC, types=["optics"])
    found = samples(scrape(device))
    labels = labels_of(found, "pyez_junos_interface_temperature_celsius", interface="xe-0/2/0")
    # Same label set as the legacy interface collector, so dashboards keep working.
    assert labels == {
        "interface": "xe-0/2/0",
        "description": "Core: core-3 (OSPFed) via K1:DWDM",
        "MAC": "00:00:5e:00:53:3f",
        "speed": "10Gbps",
    }
    assert value(found, "pyez_junos_interface_temperature_celsius", interface="xe-0/2/0") == 41
    assert value(found, "pyez_junos_interface_receiving_optic_power_dbm", interface="xe-0/2/0") == -30
    assert (
        value(found, "pyez_junos_interface_optics_alarm", interface="xe-0/2/0", alarm="laser_rx_power_low_alarm") == 1
    )
    assert (
        value(found, "pyez_junos_interface_optics_alarm", interface="xe-0/2/0", alarm="laser_tx_power_low_alarm") == 0
    )
    # One optics RPC and the cheap interface list, not show interfaces detail.
    assert sorted(set(device.device.rpc.calls)) == ["interfaces_brief", "optics"]


def test_missing_interface_statistics_are_reported_and_unnamed_queues_skipped(tmp_path):
    (tmp_path / "interface_extensive.xml").write_text("""<interface-information><physical-interface>
      <name>et-0/0/0</name><description>Core: peer</description>
      <queue><queue-counters-tail-drop-packets>99</queue-counters-tail-drop-packets></queue>
      </physical-interface></interface-information>""")
    device = make_device(tmp_path, types=["interface_errors"])
    found = samples(scrape(device))
    assert "pyez_junos_interface_errors_total" not in found
    assert "pyez_junos_interface_queue_packets_total" not in found
    assert device.schema.missing == {
        ("interface_extensive", "input-error-list"): 1,
        ("interface_extensive", "output-error-list"): 1,
    }


def test_logical_interfaces_without_name_or_counters_are_not_exported(tmp_path):
    (tmp_path / "logical_interfaces_lo0.xml").write_text("""<interface-information>
      <logical-interface><traffic-statistics><input-bytes>12</input-bytes></traffic-statistics></logical-interface>
      <logical-interface><name>lo0.0</name></logical-interface></interface-information>""")
    device = make_device(tmp_path, types=["logical_interfaces"], options={"logical_interfaces": ["lo0"]})
    found = samples(scrape(device))
    assert "pyez_junos_logical_interface_received_bytes_total" not in found
    assert device.schema.missing == {
        ("logical_interfaces", "name"): 1,
        ("logical_interfaces", "logical-interface/traffic-statistics"): 1,
    }


def test_unknown_lacp_states_remain_bounded_and_are_reported(tmp_path):
    original = (SYNTHETIC / "lacp.xml").read_text()
    (tmp_path / "lacp.xml").write_text(
        original.replace("Collecting distributing", "NewMux").replace("Current", "NewReceive")
    )
    device = make_device(tmp_path, types=["lacp"])
    found = samples(scrape(device))
    assert value(found, "pyez_junos_lacp_member_mux_state", interface="xe-0/0/0", state="unknown") == 1
    assert value(found, "pyez_junos_lacp_member_receive_state", interface="xe-0/0/0", state="unknown") == 1
    assert value(found, "pyez_junos_lacp_member_distributing", interface="xe-0/0/0") == 0
    assert ("lacp", "lacp-mux-state:unexpected-value") in device.schema.missing
    assert ("lacp", "lacp-receive-state:unexpected-value") in device.schema.missing


def test_mac_summary_xml_keeps_vlan_and_counter_names(tmp_path):
    (tmp_path / "mac_table_summary.xml").write_text("""<ethernet-switching-table-information>
      <vlan><vlan-name>servers</vlan-name><vlan-id>100</vlan-id><mac-count>7</mac-count>
        <learned-entries>6</learned-entries></vlan></ethernet-switching-table-information>""")
    found = samples(scrape(make_device(tmp_path, types=["vxlan"])))
    assert value(found, "pyez_junos_mac_table", vlan="servers", field="mac_count") == 7
    assert value(found, "pyez_junos_mac_table", vlan="servers", field="learned_entries") == 6
    assert len(found["pyez_junos_mac_table"]) == 2
