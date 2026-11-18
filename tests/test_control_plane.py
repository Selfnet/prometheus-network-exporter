"""Routing engine, processes, FPC, alarms, core dumps, uptime, storage, NTP, probe."""

import pytest

from prometheus_network_exporter.collectors.junos.system import (
    core_process,
    parse_size,
    parse_top,
    process_name,
)

from .conftest import CONTROL_PLANE_TYPES, SYNTHETIC, labels_of, make_device, samples, scrape, value


@pytest.fixture
def control_plane():
    return samples(scrape(make_device(SYNTHETIC, types=CONTROL_PLANE_TYPES)))


def test_routing_engine(control_plane):
    cpu = "pyez_junos_re_cpu_ratio"
    assert value(control_plane, cpu, slot="0", mode="interrupt", window="current") == 0.05
    assert value(control_plane, cpu, slot="0", mode="kernel", window="current") == 0.15
    assert value(control_plane, cpu, slot="0", mode="kernel", window="1m") == 0.12
    # 5m and 15m are not in the fixture and must be absent, not 0.
    assert not [labels for labels, _ in control_plane[cpu] if labels["window"] == "5m"]
    assert value(control_plane, "pyez_junos_re_load_average", slot="0", window="1m") == 1.2
    assert value(control_plane, "pyez_junos_re_memory_utilization_ratio", slot="0") == 0.27
    assert value(control_plane, "pyez_junos_re_temperature_celsius", slot="0", sensor="cpu") == 61
    info = labels_of(control_plane, "pyez_junos_re_info", slot="0")
    assert info["mastership_state"] == "master"
    assert info["last_reboot_reason"] == "0x4000:VJUNOS reboot"


def test_processes(control_plane):
    # Threads add up: fxpc{fxpc} 12.5 % + fxpc{TraceRoute Thread} 3 %.
    assert value(control_plane, "pyez_junos_process_cpu_ratio", process="fxpc") == pytest.approx(0.155)
    assert value(control_plane, "pyez_junos_process_threads", process="fxpc") == 2
    assert value(control_plane, "pyez_junos_process_resident_bytes", process="rpd") == 40404 * 1024
    names = {labels["process"] for labels, _ in control_plane["pyez_junos_process_cpu_ratio"]}
    assert "idle" not in names
    assert {"rpd", "fxpc", "chassisd", "ppmd", "sshd"} <= names


def test_fpc(control_plane):
    assert value(control_plane, "pyez_junos_fpc_state", slot="0", state="Online") == 1
    assert value(control_plane, "pyez_junos_fpc_state", slot="1", state="Empty") == 1
    assert value(control_plane, "pyez_junos_fpc_cpu_ratio", slot="0", window="current") == 0.22
    assert value(control_plane, "pyez_junos_fpc_cpu_interrupt_ratio", slot="0") == 0.04
    assert value(control_plane, "pyez_junos_fpc_memory_utilization_ratio", slot="0", type="heap") == 0.35
    # An empty slot has no CPU.
    assert not [labels for labels, _ in control_plane["pyez_junos_fpc_cpu_ratio"] if labels["slot"] == "1"]


def test_alarms(control_plane):
    assert value(control_plane, "pyez_junos_alarms_active", source="chassis", **{"class": "Major"}) == 1
    assert value(control_plane, "pyez_junos_alarms_active", source="system", **{"class": "Major"}) == 0
    assert (
        value(
            control_plane,
            "pyez_junos_alarm_since_timestamp_seconds",
            description="xe-0/2/0: Rx power low",
        )
        == 1791810000
    )


def test_core_dumps(control_plane):
    assert value(control_plane, "pyez_junos_core_dumps", process="rpd") == 2
    assert value(control_plane, "pyez_junos_core_dumps", process="fxpc") == 1
    assert value(control_plane, "pyez_junos_core_dump_newest_timestamp_seconds", process="rpd") == 1791750000
    assert "README" not in {labels["process"] for labels, _ in control_plane["pyez_junos_core_dumps"]}


def test_uptime_and_commit(control_plane):
    assert value(control_plane, "pyez_junos_system_time_seconds") == 1791925876
    assert value(control_plane, "pyez_junos_system_booted_timestamp_seconds") == 1791749455
    assert value(control_plane, "pyez_junos_last_commit_timestamp_seconds") == 1791850000
    assert labels_of(control_plane, "pyez_junos_last_commit_info")["user"] == "adrian"


def test_storage_keeps_only_writable_mounts(control_plane):
    mounts = {labels["mount"] for labels, _ in control_plane["pyez_junos_storage_used_ratio"]}
    assert mounts == {"/.mount", "/.mount/var"}
    assert value(control_plane, "pyez_junos_storage_used_ratio", mount="/.mount/var") == 0.93


def test_storage_includes_a_root_mount(tmp_path):
    # Older releases mount the writable root on / instead of /.mount.
    (tmp_path / "storage.xml").write_text(
        "<rpc-reply><system-storage-information>"
        "<filesystem><filesystem-name>/dev/da0s1a</filesystem-name>"
        "<used-percent>41</used-percent><mounted-on>/</mounted-on></filesystem>"
        "<filesystem><filesystem-name>/dev/da0s1f</filesystem-name>"
        "<used-percent>12</used-percent><mounted-on>/var</mounted-on></filesystem>"
        "<filesystem><filesystem-name>devfs</filesystem-name>"
        "<used-percent>100</used-percent><mounted-on>/dev</mounted-on></filesystem>"
        "</system-storage-information></rpc-reply>"
    )
    found = samples(scrape(make_device(tmp_path, types=["system"])))
    mounts = {labels["mount"] for labels, _ in found["pyez_junos_storage_used_ratio"]}
    assert mounts == {"/", "/var"}
    assert value(found, "pyez_junos_storage_used_ratio", mount="/") == 0.41


def test_ntp(control_plane):
    assert value(control_plane, "pyez_junos_ntp_synced") == 1
    assert value(control_plane, "pyez_junos_ntp_offset_seconds") == pytest.approx(-0.00125)
    assert value(control_plane, "pyez_junos_ntp_stratum") == 3


def test_probe(control_plane):
    assert value(control_plane, "pyez_junos_probe_success") == 1
    assert value(control_plane, "pyez_junos_probe_rpc_seconds") >= 0


def test_probe_reports_failure(tmp_path):
    found = samples(scrape(make_device(tmp_path, types=["probe"])))
    assert value(found, "pyez_junos_probe_success") == 0
    assert value(found, "pyez_junos_rpc_failed", rpc="probe") == 1


def test_ntp_unsynchronised(tmp_path):
    (tmp_path / "ntp_status.xml").write_text(
        "<rpc-reply><output>assID=0 status=c016 leap_alarm, sync_unspec, 1 event,\n"
        "stratum=16, offset=0.000</output></rpc-reply>"
    )
    found = samples(scrape(make_device(tmp_path, types=["system"])))
    assert value(found, "pyez_junos_ntp_synced") == 0


@pytest.mark.parametrize(
    "command, expected",
    [
        ("fxpc{fxpc}", "fxpc"),
        ("/usr/sbin/rpd -N", "rpd"),
        ("idle{idle: cpu0}", "idle"),
        ("[kernel]", "kernel"),
    ],
)
def test_process_name(command, expected):
    assert process_name(command) == expected


def test_parse_size():
    assert parse_size("155M") == 155 * 1024**2
    assert parse_size("40404K") == 40404 * 1024
    assert parse_size("12") == 12 * 1024
    assert parse_size("n/a") is None


def test_parse_top_without_header_is_empty():
    assert parse_top("no process table here") == {}


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/var/crash/core.rpd.0.gz", "rpd"),
        ("/var/crash/fxpc.core.0.gz", "fxpc"),
        ("/var/tmp/core-chassisd.1.gz", "chassisd"),
        ("vmcore.0.gz", "vmcore"),
    ],
)
def test_core_process(path, expected):
    assert core_process(path) == expected


def test_core_dumps_text_ignores_messages(tmp_path):
    (tmp_path / "core_dumps.xml").write_text(
        "<rpc-reply><output>/var/crash/*core*: No such file or directory\n"
        "-rw-r--r--  1 root  wheel  1234567 Oct 11 08:26 /var/tmp/core.rpd.0.gz\n"
        "/var/tmp/pics/*core*: No such file or directory\n"
        "</output></rpc-reply>"
    )
    found = samples(scrape(make_device(tmp_path, types=["core_dumps"])))
    assert [(labels["process"], v) for labels, v in found["pyez_junos_core_dumps"]] == [("rpd", 1.0)]


def test_core_dumps_none_in_xml(tmp_path):
    (tmp_path / "core_dumps.xml").write_text(
        "<rpc-reply><directory-list><output>/var/crash/*core*: No such file or directory</output>"
        "</directory-list></rpc-reply>"
    )
    found = samples(scrape(make_device(tmp_path, types=["core_dumps"])))
    assert "pyez_junos_core_dumps" not in found
