from .conftest import labels_of, value


def test_sessions(synthetic):
    assert value(synthetic, "pyez_junos_bfd_sessions") == 2
    assert value(synthetic, "pyez_junos_bfd_clients") == 2
    assert value(synthetic, "pyez_junos_bfd_session_up", neighbor="198.51.100.2", interface="ae0.0", client="OSPF") == 1
    assert value(synthetic, "pyez_junos_bfd_session_up", neighbor="192.0.2.105", interface="", client="BGP") == 0
    assert value(synthetic, "pyez_junos_bfd_session_detection_time_seconds", neighbor="198.51.100.2") == 1.5
    assert value(synthetic, "pyez_junos_bfd_session_transmit_interval_seconds", neighbor="192.0.2.105") == 1.0
    assert value(synthetic, "pyez_junos_bfd_session_up_seconds", neighbor="198.51.100.2") == 86400
    assert not [l for l, _ in synthetic["pyez_junos_bfd_session_up_seconds"] if l["neighbor"] == "192.0.2.105"]
    info = labels_of(synthetic, "pyez_junos_bfd_session_info", neighbor="192.0.2.105")
    assert info["state"] == "Down"
    assert info["local_diagnostic"] == "CtlExpire"
    assert info["remote_state"] == "Down"
