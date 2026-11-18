"""Transceiver inventory against the device: one PIC detail RPC per PIC."""

from prometheus_network_exporter.collectors.junos.rpcs import fixture_name

from .conftest import make_device, samples, scrape

INVENTORY = """<rpc-reply><chassis-inventory><chassis><name>Chassis</name>
  <chassis-module><name>FPC 0</name>
    <chassis-sub-module><name>PIC 0</name>
      <chassis-sub-sub-module><name>Xcvr 0</name><part-number>NON-JNPR</part-number>
        <serial-number>serial-0</serial-number><description>SFP+-10G-LR</description></chassis-sub-sub-module>
    </chassis-sub-module>
    <chassis-sub-module><name>PIC 1</name>
      <chassis-sub-sub-module><name>Xcvr 2</name><part-number>NON-JNPR</part-number>
        <serial-number>serial-2</serial-number><description>QSFP+-40G-SR4</description></chassis-sub-sub-module>
    </chassis-sub-module>
  </chassis-module></chassis></chassis-inventory></rpc-reply>"""
PIC_1 = """<rpc-reply><fpc-information><fpc><pic-detail><port-information><port>
  <port-number>2</port-number><sfp-vendor-name>Example</sfp-vendor-name>
  <sfp-vendor-pno>PART-40G-SR4</sfp-vendor-pno></port></port-information></pic-detail></fpc>
  </fpc-information></rpc-reply>"""
INTERFACES = """<rpc-reply><interface-information>
  <physical-interface><name>xe-0/0/0</name></physical-interface>
  <physical-interface><name>et-0/1/2</name></physical-interface>
  </interface-information></rpc-reply>"""


def device(tmp_path):
    (tmp_path / "transceivers.xml").write_text(INVENTORY)
    # PIC 0 rejects the RPC: no fixture means RpcError.
    (tmp_path / "transceiver_pic_0_1.xml").write_text(PIC_1)
    (tmp_path / "interfaces_brief.xml").write_text(INTERFACES)
    return make_device(tmp_path, types=["transceivers"], options={"optics_interval_seconds": 0})


def info(found):
    return {labels["module"]: labels for labels, _ in found["pyez_junos_transceiver_info"]}


def test_each_pic_has_its_own_rpc_name():
    names = {
        fixture_name("get_pic_detail", {"fpc_slot": fpc, "pic_slot": pic})
        for fpc, pic in [("0", "0"), ("0", "1"), ("1", "0")]
    }
    assert names == {"transceiver_pic_0_0", "transceiver_pic_0_1", "transceiver_pic_1_0"}


def test_failing_pic_does_not_block_the_others(tmp_path):
    dev = device(tmp_path)
    for _ in range(2):
        found = samples(scrape(dev))
        modules = info(found)
        assert modules["0/1/2"]["manufacturer"] == "Example"
        assert modules["0/1/2"]["part_number"] == "PART-40G-SR4"
        assert modules["0/0/0"]["part_number"] == "NON-JNPR"
        failed = {labels["rpc"] for labels, value in found["pyez_junos_rpc_failed"] if value == 1}
        assert "transceiver_pic_0_0" in failed and "transceiver_pic_0_1" not in failed
    calls = dev.device.rpc.calls
    # PIC 1 is asked on every scrape, PIC 0 only once until its retry time.
    assert calls.count("transceiver_pic_0_1") == 2
    assert calls.count("transceiver_pic_0_0") == 1
