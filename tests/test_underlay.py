"""LDP, l2circuit and PIM."""

import pytest

from .conftest import CONTROL_PLANE_TYPES, SYNTHETIC, labels_of, make_device, samples, scrape, value


@pytest.fixture
def found():
    return samples(scrape(make_device(SYNTHETIC, types=CONTROL_PLANE_TYPES)))


def test_ldp_sessions(found):
    assert value(found, "pyez_junos_ldp_sessions") == 2
    assert value(found, "pyez_junos_ldp_session_state", neighbor="192.0.2.101", state="Operational") == 1
    assert value(found, "pyez_junos_ldp_session_state", neighbor="192.0.2.109", state="Nonexistent") == 1
    assert value(found, "pyez_junos_ldp_session_up_seconds", neighbor="192.0.2.101") == 86400
    assert not [l for l, _ in found["pyez_junos_ldp_session_up_seconds"] if l["neighbor"] == "192.0.2.109"]


def test_ldp_neighbors(found):
    assert value(found, "pyez_junos_ldp_neighbors", interface="et-0/0/26.0") == 1
    assert value(found, "pyez_junos_ldp_neighbor_hold_remaining_seconds", interface="et-0/0/26.0") == 12


def test_l2circuit(found):
    assert value(found, "pyez_junos_l2circuit_up", connection="xe-0/0/22.0(vc 1)") == 1
    assert value(found, "pyez_junos_l2circuit_up", connection="xe-0/0/23.0(vc 2)") == 0
    assert value(found, "pyez_junos_l2circuit_up_transitions_total", connection="xe-0/0/22.0(vc 1)") == 3
    assert labels_of(found, "pyez_junos_l2circuit_info", connection="xe-0/0/23.0(vc 2)")["status"] == "RD"


def test_pim(found):
    assert value(found, "pyez_junos_pim_neighbors", interface="et-0/0/26.0") == 1
    assert value(found, "pyez_junos_pim_neighbors", interface="xe-0/2/0.0") == 0
    assert value(found, "pyez_junos_pim_neighbor_up_seconds", interface="et-0/0/26.0", neighbor="198.51.100.2") == 3600


def test_unknown_ldp_state_is_bounded(tmp_path):
    (tmp_path / "ldp_session.xml").write_text(
        "<rpc-reply><ldp-session-information><ldp-session>"
        "<ldp-neighbor-address>192.0.2.101</ldp-neighbor-address>"
        "<ldp-session-state>Wobbly</ldp-session-state>"
        "</ldp-session></ldp-session-information></rpc-reply>"
    )
    device = make_device(tmp_path, types=["ldp"])
    result = samples(scrape(device))
    assert value(result, "pyez_junos_ldp_session_state", neighbor="192.0.2.101", state="unknown") == 1
    assert ("ldp", "ldp-session-state:unexpected-value") in device.schema.missing
