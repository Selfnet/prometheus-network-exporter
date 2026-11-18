"""TCP connection states read from /proc/net/tcp and tcp6."""

import os

import pytest

from prometheus_network_exporter import netstat

HEADER = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
UID = os.getuid()
# 192.0.2.10:40000 -> 198.51.100.1:22 established, 192.0.2.10:9332 listening.
TCP = HEADER + (
    f"   0: 0A0200C0:9C40 016433C6:0016 01 00000000:00000000 00:00000000 00000000 {UID:5d} 0 1001 1\n"
    f"   1: 0A0200C0:2474 00000000:0000 0A 00000000:00000000 00:00000000 00000000 {UID:5d} 0 1002 1\n"
    f"   2: 0A0200C0:9C41 016433C6:01BB 06 00000000:00000000 00:00000000 00000000 {UID:5d} 0 1003 1\n"
)
# [2001:db8::1]:40001 -> [2001:db8::2]:443 established.
TCP6 = HEADER + (
    "   0: B80D0120000000000000000001000000:9C41 B80D0120000000000000000002000000:01BB 01 "
    f"00000000:00000000 00:00000000 00000000 {UID:5d} 0 2001 1\n"
)


@pytest.fixture
def proc(tmp_path, monkeypatch):
    v4, v6 = tmp_path / "tcp", tmp_path / "tcp6"
    v4.write_text(TCP)
    v6.write_text(TCP6)
    monkeypatch.setattr(netstat, "PROC_TCP", str(v4))
    monkeypatch.setattr(netstat, "PROC_TCP6", str(v6))


def test_addresses_are_decoded():
    assert netstat.ipv4("0A0200C0") == "192.0.2.10"
    assert netstat.ipv6("B80D0120000000000000000001000000") == "2001:db8::1"
    assert netstat._ip("0100007F") == "127.0.0.1"
    assert netstat._ip("abc") is None
    assert netstat._convert_ip_port("0A0200C0:0016") == ("192.0.2.10", "22")


def test_connections(proc):
    connections = list(netstat.netstat(v4=True))
    assert [c["state"] for c in connections] == ["ESTABLISHED", "LISTEN", "TIME_WAIT"]
    first = connections[0]
    assert (first["local_host"], first["local_port"]) == ("192.0.2.10", 40000)
    assert (first["remote_host"], first["remote_port"]) == ("198.51.100.1", 22)
    assert first["uid"] and first["executable"] is None
    v6 = list(netstat.netstat(v6=True))
    assert v6[0]["remote_host"] == "2001:db8::2"


def test_ssh_and_http_filters(proc):
    assert [c["remote_port"] for c in netstat.ssh(v4=True)] == [22]
    assert [c["remote_port"] for c in netstat.http(v4=True)] == [443]
    assert [c["remote_port"] for c in netstat.http(v6=True)] == [443]


def test_family_must_be_given_once():
    with pytest.raises(Exception):
        netstat._load(v4=True, v6=True)
    with pytest.raises(Exception):
        netstat._load()


def test_missing_procfs_reports_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(netstat, "PROC_TCP", str(tmp_path / "absent"))
    assert list(netstat.netstat(v4=True)) == []


def test_lookup_falls_back_to_the_address(monkeypatch):
    def fail(address):
        raise OSError

    monkeypatch.setattr(netstat.socket, "gethostbyaddr", fail)
    assert netstat.lookup("192.0.2.1") == "192.0.2.1"
    monkeypatch.setattr(netstat.socket, "gethostbyaddr", lambda address: ("host.example.net", [], [address]))
    assert netstat.lookup("192.0.2.1") == "host.example.net"


def test_pid_of_inode(monkeypatch):
    monkeypatch.setattr(netstat.glob, "glob", lambda pattern: ["/proc/42/fd/3", "/proc/43/fd/4"])
    links = {"/proc/42/fd/3": "pipe:[1]", "/proc/43/fd/4": "socket:[1002]"}
    monkeypatch.setattr(netstat.os, "readlink", lambda path: links[path])
    assert netstat._get_pid_of_inode("1002") == "43"
    assert netstat._get_pid_of_inode("9999") is None
