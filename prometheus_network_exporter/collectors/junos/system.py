"""Control plane metrics: routing engine, processes, FPC, alarms and system state.

These collectors exist to locate control plane stalls: which share of the
routing engine CPU goes to user space, kernel or interrupts, which daemon is
busy, whether the PFE CPU is loaded, and whether the box raised an alarm,
dumped a core or had its configuration changed.
"""

from __future__ import annotations

import collections
import os
import re
from typing import Dict, Iterable, Optional

from prometheus_client.core import GaugeMetricFamily, InfoMetricFamily

from ..base import Collector
from . import base
from .rpcs import RPCS
from .xmlutil import (
    Reader,
    add,
    all_text,
    find,
    iter_items,
    label,
    localname,
    number,
    seconds,
    state_set,
    text,
)

# cpu-user is the current value, cpu-user1/2/3 the 1, 5 and 15 minute
# averages that newer releases add.
CPU_MODES = (
    ("user", "cpu-user"),
    ("background", "cpu-background"),
    ("kernel", "cpu-system"),
    ("interrupt", "cpu-interrupt"),
    ("idle", "cpu-idle"),
)
CPU_WINDOWS = (("current", ""), ("1m", "1"), ("5m", "2"), ("15m", "3"))
LOAD_AVERAGES = (
    ("1m", "load-average-one"),
    ("5m", "load-average-five"),
    ("15m", "load-average-fifteen"),
)

DEFAULT_PROCESSES = (
    "rpd",
    "mgd",
    "chassisd",
    "dcd",
    "fxpc",
    "pfed",
    "ppmd",
    "bfdd",
    "l2ald",
    "l2cpd",
    "lacpd",
    "snmpd",
    "mib2d",
    "eventd",
    "jdhcpd",
    "sshd",
    "kernel",
)
DEFAULT_PROCESS_TOP = 10
SIZE_UNITS = {"": 1024, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "B": 1}

FPC_STATES = ("Online", "Offline", "Empty", "Present", "Diagnostics", "Check", "Testing")
FPC_CPU_WINDOWS = (
    ("current", "cpu-total"),
    ("1m", "cpu-1min-avg"),
    ("5m", "cpu-5min-avg"),
    ("15m", "cpu-15min-avg"),
)

ALARM_CLASSES = ("Major", "Minor")
LS_LINE = re.compile(r"^\s*[-l][rwxsStT-]{9}\S*\s+\d+\s+.*\s(?P<path>/\S+)\s*$")
DEFAULT_STORAGE_MOUNTS = r"^(/\.mount)?(/var|/var/log|/tmp|/config)?$"


def _ratio(value: Optional[float]) -> Optional[float]:
    return None if value is None else value / 100.0


class RoutingEngineCollector(Collector):
    """``show chassis routing-engine``: CPU split by mode, load and memory."""

    name = "route_engine"

    def __init__(self, device):
        super().__init__(f"{base}_re", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        command, args = RPCS["route_engine"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        read = self.reader
        labels = ["slot"]
        cpu = GaugeMetricFamily(
            f"{self.base_name}_cpu_ratio",
            "Routing engine CPU share per mode; window current is the last few "
            "seconds, 1m/5m/15m are averages where the release reports them",
            labels=labels + ["mode", "window"],
        )
        load = GaugeMetricFamily(
            f"{self.base_name}_load_average",
            "Routing engine load average",
            labels=labels + ["window"],
        )
        memory = GaugeMetricFamily(
            f"{self.base_name}_memory_utilization_ratio",
            "Routing engine memory utilisation",
            labels=labels,
        )
        up = GaugeMetricFamily(
            f"{self.base_name}_up_seconds", "Routing engine uptime", labels=labels
        )
        temperature = GaugeMetricFamily(
            f"{self.base_name}_temperature_celsius",
            "Routing engine and CPU temperature",
            labels=labels + ["sensor"],
        )
        info = InfoMetricFamily(
            self.base_name, "Routing engine model, mastership and reboot reason", labels=labels
        )
        for engine in iter_items(reply, ("route-engine",)):
            slot = [label(read.text(engine, "slot", required=False) or "0")]
            for mode, field in CPU_MODES:
                for window, suffix in CPU_WINDOWS:
                    value = (
                        read.number(engine, field)
                        if not suffix
                        else number(text(engine, field + suffix))
                    )
                    add(cpu, slot + [mode, window], _ratio(value))
            for window, field in LOAD_AVERAGES:
                add(load, slot + [window], read.number(engine, field))
            utilisation = read.first_text(
                engine, ("memory-buffer-utilization", "memory-system-total-util")
            )
            add(memory, slot, _ratio(number(utilisation)))
            add(up, slot, read.seconds(engine, "up-time", required=False))
            for sensor, field in (("re", "temperature"), ("cpu", "cpu-temperature")):
                found = find(engine, field)
                if found is not None:
                    add(temperature, slot + [sensor], seconds_like(found, "celsius"))
            info.add_metric(
                slot,
                {
                    "model": label(read.text(engine, "model", required=False)),
                    "mastership_state": label(
                        read.text(engine, "mastership-state", required=False)
                    ),
                    "last_reboot_reason": label(
                        read.text(engine, "last-reboot-reason", required=False)
                    ),
                },
            )
        yield from read.unique((cpu, load, memory, up, temperature, info))


def seconds_like(element, attribute: str) -> Optional[float]:
    """Numeric value of a ``junos:<attribute>`` attribute, falling back to the text."""
    for key, value in element.attrib.items():
        if key == attribute or key.endswith("}" + attribute):
            return number(value)
    return number(element.text)


def parse_size(value: str) -> Optional[float]:
    """``155M`` -> bytes; ``top`` prints kilobytes without a unit."""
    match = re.fullmatch(r"([\d.]+)([KMGTB]?)", value.strip())
    if not match:
        return None
    return float(match.group(1)) * SIZE_UNITS[match.group(2)]


def process_name(command: str) -> str:
    """``fxpc{fxpc}`` -> ``fxpc``, ``/usr/sbin/rpd -N`` -> ``rpd``, ``[idle]`` -> ``idle``."""
    match = re.match(r"\s*\[?([^\s{\]]+)", command)
    if not match:
        return ""
    return os.path.basename(match.group(1)).rstrip(":")


def parse_top(output: str) -> Dict[str, dict]:
    """Aggregate ``top``-style process lines per process name.

    CPU shares of threads add up; resident memory is shared between the
    threads of a process, so the largest value is kept.
    """
    lines = output.splitlines()
    header_index = next(
        (i for i, line in enumerate(lines) if "PID" in line.split() and "COMMAND" in line.split()),
        None,
    )
    result: Dict[str, dict] = {}
    if header_index is None:
        return result
    columns = lines[header_index].split()
    for line in lines[header_index + 1:]:
        parts = line.split(None, len(columns) - 1)
        if len(parts) != len(columns) or not parts[0].isdigit():
            continue
        row = dict(zip(columns, parts))
        name = process_name(row["COMMAND"])
        if not name:
            continue
        entry = result.setdefault(name, {"cpu": 0.0, "resident": None, "threads": 0})
        cpu = number((row.get("WCPU") or row.get("CPU") or "").rstrip("%"))
        if cpu is not None:
            entry["cpu"] += cpu / 100.0
        resident = parse_size(row.get("RES", ""))
        if resident is not None:
            entry["resident"] = max(entry["resident"] or 0.0, resident)
        entry["threads"] += int(number(row.get("THR")) or 1)
    return result


class ProcessCollector(Collector):
    """``show system processes extensive``: CPU and memory of the busy daemons.

    Exports a fixed list of daemons plus the top N by CPU, so a daemon that
    is not on the list still shows up while it is busy.
    """

    name = "processes"

    def __init__(self, device, processes: Iterable[str] = DEFAULT_PROCESSES, top: int = DEFAULT_PROCESS_TOP):
        super().__init__(f"{base}_process", device, config={})
        self.reader = Reader(device.schema, self.name)
        self.processes = list(processes)
        self.top = int(top)

    def collect(self):
        command, args = RPCS["processes"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        processes = parse_top(all_text(reply))
        if not processes:
            self.reader.record("output:process-table")
            return
        busiest = sorted(
            (name for name in processes if name != "idle"),
            key=lambda name: processes[name]["cpu"],
            reverse=True,
        )
        selected = [name for name in self.processes if name in processes]
        selected += [name for name in busiest[: self.top] if name not in selected]
        cpu = GaugeMetricFamily(
            f"{self.base_name}_cpu_ratio",
            "Weighted CPU share of the process, summed over its threads; "
            "1.0 is one core",
            labels=["process"],
        )
        resident = GaugeMetricFamily(
            f"{self.base_name}_resident_bytes", "Resident memory of the process", labels=["process"]
        )
        threads = GaugeMetricFamily(
            f"{self.base_name}_threads", "Threads of the process", labels=["process"]
        )
        for name in selected:
            entry = processes[name]
            cpu.add_metric([name], entry["cpu"])
            add(resident, [name], entry["resident"])
            threads.add_metric([name], float(entry["threads"]))
        count = GaugeMetricFamily(
            f"{base}_processes", "Distinct process names in the process table"
        )
        count.add_metric([], float(len(processes)))
        yield from self.reader.unique((cpu, resident, threads, count))


class FPCCollector(Collector):
    """``show chassis fpc``: PFE CPU, memory, temperature and state."""

    name = "fpc"

    def __init__(self, device):
        super().__init__(f"{base}_fpc", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        command, args = RPCS["fpc"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        read = self.reader
        labels = ["slot"]
        state = GaugeMetricFamily(
            f"{self.base_name}_state", "FPC state, 1 for the current one", labels=labels + ["state"]
        )
        cpu = GaugeMetricFamily(
            f"{self.base_name}_cpu_ratio", "FPC CPU utilisation", labels=labels + ["window"]
        )
        interrupt = GaugeMetricFamily(
            f"{self.base_name}_cpu_interrupt_ratio", "FPC CPU share spent in interrupts", labels=labels
        )
        memory = GaugeMetricFamily(
            f"{self.base_name}_memory_utilization_ratio",
            "FPC heap and buffer utilisation",
            labels=labels + ["type"],
        )
        temperature = GaugeMetricFamily(
            f"{self.base_name}_temperature_celsius", "FPC temperature", labels=labels
        )
        for fpc in iter_items(reply, ("fpc",)):
            slot = [label(read.text(fpc, "slot"))]
            current = read.text(fpc, "state")
            if not state_set(state, slot, current, FPC_STATES):
                read.unexpected_state("state", current)
            if (current or "").lower() != "online":
                continue
            for window, field in FPC_CPU_WINDOWS:
                add(cpu, slot + [window], _ratio(read.number(fpc, field, required=window == "current")))
            add(interrupt, slot, _ratio(read.number(fpc, "cpu-interrupt", required=False)))
            for kind in ("heap", "buffer"):
                add(
                    memory,
                    slot + [kind],
                    _ratio(read.number(fpc, f"memory-{kind}-utilization", required=False)),
                )
            found = find(fpc, "temperature")
            if found is not None:
                add(temperature, slot, seconds_like(found, "celsius"))
        yield from read.unique((state, cpu, interrupt, memory, temperature))


class AlarmCollector(Collector):
    """``show chassis alarms`` and ``show system alarms``."""

    name = "alarms"
    SOURCES = (("chassis", "chassis_alarms"), ("system", "system_alarms"))

    def __init__(self, device):
        super().__init__(f"{base}_alarm", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        read = self.reader
        active = GaugeMetricFamily(
            f"{base}_alarms_active", "Active alarms per class", labels=["source", "class"]
        )
        info = InfoMetricFamily(
            self.base_name,
            "One sample per active alarm",
            labels=["source", "class", "type", "description"],
        )
        since = GaugeMetricFamily(
            f"{self.base_name}_since_timestamp_seconds",
            "Unix time the alarm was raised",
            labels=["source", "class", "type", "description"],
        )
        for source, rpc in self.SOURCES:
            command, args = RPCS[rpc]
            reply = self.device.rpc_reply(command, **args)
            if reply is None:
                continue
            counts = collections.Counter({klass: 0 for klass in ALARM_CLASSES})
            for alarm in iter_items(reply, ("alarm-detail",)):
                klass = label(read.text(alarm, "alarm-class"))
                counts[klass] += 1
                labels = [
                    source,
                    klass,
                    label(read.text(alarm, "alarm-type", required=False)),
                    label(read.text(alarm, "alarm-description")),
                ]
                info.add_metric(labels, {})
                add(since, labels, read.seconds(alarm, "alarm-time", required=False))
            for klass, count in sorted(counts.items()):
                active.add_metric([source, klass], float(count))
        yield from read.unique((active, info, since))


def core_process(path: str) -> str:
    """``/var/crash/core.rpd.0.gz`` and ``rpd.core.0.gz`` -> ``rpd``."""
    name = os.path.basename(path)
    name = re.sub(r"^core[.-]", "", name)
    return name.split(".", 1)[0] or name


class CoreDumpCollector(Collector):
    """``show system core-dumps``: crashed daemons."""

    name = "core_dumps"

    def __init__(self, device):
        super().__init__(f"{base}_core_dump", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        command, args = RPCS["core_dumps"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        counts, newest = self._scan(reply)
        dumps = GaugeMetricFamily(
            f"{base}_core_dumps", "Core dump files on the device", labels=["process"]
        )
        for process, count in sorted(counts.items()):
            dumps.add_metric([process], float(count))
        latest = GaugeMetricFamily(
            f"{self.base_name}_newest_timestamp_seconds",
            "Unix time of the newest core dump of the process",
            labels=["process"],
        )
        for process, stamp in sorted(newest.items()):
            latest.add_metric([process], stamp)
        yield from self.reader.unique((dumps, latest))

    @staticmethod
    def _scan(reply):
        """Core files per process and the newest file date per process."""
        counts = collections.Counter()
        newest: Dict[str, float] = {}
        files = list(iter_items(reply, ("file-information",)))
        for item in files:
            path = text(item, "file-name") or ""
            if "core" not in os.path.basename(path):
                continue
            process = core_process(path)
            counts[process] += 1
            stamp = seconds(item, "file-date")
            if stamp is not None:
                newest[process] = max(newest.get(process, stamp), stamp)
        if files or list(iter_items(reply, ("directory-list", "directory"))):
            return counts, newest
        # Text listing in ls -l style; the date there has no year, so only
        # counts. Only lines that look like a file entry count, never messages
        # such as "/var/crash/*core*: No such file or directory".
        for line in all_text(reply).splitlines():
            match = LS_LINE.match(line)
            if match and "core" in os.path.basename(match.group("path")):
                counts[core_process(match.group("path"))] += 1
        return counts, newest


class UptimeCollector(Collector):
    """``show system uptime``: device clock, boot time and the last commit."""

    name = "uptime"

    def __init__(self, device):
        super().__init__(f"{base}_system", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        command, args = RPCS["uptime"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        read = self.reader
        labels = ["re"]
        clock = GaugeMetricFamily(
            f"{self.base_name}_time_seconds",
            "Device clock as Unix time; compare with time() for clock skew",
            labels=labels,
        )
        booted = GaugeMetricFamily(
            f"{self.base_name}_booted_timestamp_seconds", "Unix time of the last boot", labels=labels
        )
        protocols = GaugeMetricFamily(
            f"{self.base_name}_protocols_started_timestamp_seconds",
            "Unix time the routing protocols were started",
            labels=labels,
        )
        commit = GaugeMetricFamily(
            f"{base}_last_commit_timestamp_seconds",
            "Unix time of the last configuration commit",
            labels=labels,
        )
        commit_info = InfoMetricFamily(
            f"{base}_last_commit", "User of the last configuration commit", labels=labels
        )
        for uptime in iter_items(reply, ("system-uptime-information",)):
            parent = uptime.getparent()
            re_name = ""
            if parent is not None and localname(parent) == "multi-routing-engine-item":
                re_name = label(text(parent, "re-name"))
            add(clock, [re_name], read.seconds(uptime, "current-time/date-time"))
            add(booted, [re_name], read.seconds(uptime, "system-booted-time/date-time"))
            add(
                protocols,
                [re_name],
                read.seconds(uptime, "protocols-started-time/date-time", required=False),
            )
            add(
                commit,
                [re_name],
                read.seconds(uptime, "last-configured-time/date-time", required=False),
            )
            user = text(uptime, "last-configured-time/user")
            if user is not None:
                commit_info.add_metric([re_name], {"user": user})
        yield from read.unique((clock, booted, protocols, commit, commit_info))


class StorageCollector(Collector):
    """``show system storage`` for the file systems Junos writes to."""

    name = "storage"

    def __init__(self, device, mounts: str = DEFAULT_STORAGE_MOUNTS):
        super().__init__(f"{base}_storage", device, config={})
        self.reader = Reader(device.schema, self.name)
        self.mounts = re.compile(mounts)

    def collect(self):
        command, args = RPCS["storage"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        read = self.reader
        used = GaugeMetricFamily(
            f"{self.base_name}_used_ratio", "Used share of the file system", labels=["mount"]
        )
        for filesystem in iter_items(reply, ("filesystem",)):
            mount = read.text(filesystem, "mounted-on")
            if mount is None or not self.mounts.match(mount):
                continue
            add(used, [mount], _ratio(read.number(filesystem, "used-percent")))
        yield from read.unique((used,))


class NTPCollector(Collector):
    """``show ntp status``; Junos renders it as ntpq text."""

    name = "ntp"

    def __init__(self, device):
        super().__init__(f"{base}_ntp", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        command, args = RPCS["ntp_status"]
        reply = self.device.rpc_reply(command, **args)
        if reply is None:
            return
        output = all_text(reply)
        synced = GaugeMetricFamily(
            f"{self.base_name}_synced", "1 when ntpd is synchronised to a server"
        )
        offset = GaugeMetricFamily(f"{self.base_name}_offset_seconds", "Offset to the system peer")
        stratum = GaugeMetricFamily(f"{self.base_name}_stratum", "Stratum of the device")
        query_failed = GaugeMetricFamily(
            f"{self.base_name}_query_failed",
            "1 when ntpd on the device did not answer the local status query "
            "(\"localhost: timed out\"); sync state and offset are unknown then",
        )
        if re.search(r"timed out|nothing received|Connection refused", output):
            query_failed.add_metric([], 1.0)
            yield from self.reader.unique((query_failed,))
            return
        query_failed.add_metric([], 0.0)
        if "sync_ntp" in output:
            synced.add_metric([], 1.0)
        elif re.search(r"sync_(unspec|alarm|local)|leap_alarm", output):
            synced.add_metric([], 0.0)
        else:
            self.reader.record("output:sync-state")
        match = re.search(r"\boffset=\s*([-\d.]+)", output)
        if match and number(match.group(1)) is not None:
            offset.add_metric([], number(match.group(1)) / 1000.0)
        else:
            self.reader.record("output:offset")
        match = re.search(r"\bstratum=\s*(\d+)", output)
        if match:
            stratum.add_metric([], float(match.group(1)))
        yield from self.reader.unique((synced, offset, stratum, query_failed))


class ProbeCollector(Collector):
    """One cheap RPC; its duration measures how responsive the control plane is.

    Meant for its own module with a short scrape interval. Together with
    ``pyez_junos_netconf_connect_seconds`` it turns a control plane stall
    into a measurement instead of a scrape gap.
    """

    name = "probe"

    def __init__(self, device):
        super().__init__(f"{base}_probe", device, config={})

    def collect(self):
        command, args = RPCS["probe"]
        reply = self.device.rpc_reply(command, **args)
        success = GaugeMetricFamily(
            f"{self.base_name}_success", "1 when the probe RPC answered"
        )
        success.add_metric([], 0.0 if reply is None else 1.0)
        duration = GaugeMetricFamily(
            f"{self.base_name}_rpc_seconds", "Round trip time of the probe RPC"
        )
        add(duration, [], self.device.rpc_durations.get("probe"))
        yield success
        yield duration
