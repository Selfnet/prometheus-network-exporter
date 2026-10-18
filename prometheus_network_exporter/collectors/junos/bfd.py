"""BFD session metrics from ``show bfd session extensive``."""

from __future__ import annotations

from prometheus_client.core import GaugeMetricFamily, InfoMetricFamily

from ..base import Collector
from . import base
from .xmlutil import Reader, add, findall, iter_items, label, text

LABELS = ["neighbor", "interface", "client"]


class BFDCollector(Collector):
    name = "bfd"

    def __init__(self, device):
        super().__init__(f"{base}_bfd", device, config={})
        self.reader = Reader(device.schema, self.name)

    def collect(self):
        reply = self.device.rpc_reply("get_bfd_session_information", extensive=True)
        if reply is None:
            return
        read = self.reader
        sessions = GaugeMetricFamily(f"{self.base_name}_sessions", "BFD sessions")
        add(sessions, [], read.number(reply, "sessions"))
        clients = GaugeMetricFamily(f"{self.base_name}_clients", "BFD clients")
        add(clients, [], read.number(reply, "clients", required=False))
        yield from read.unique((sessions, clients))

        up = GaugeMetricFamily(
            f"{self.base_name}_session_up", "1 when the BFD session is Up", labels=LABELS
        )
        detection = GaugeMetricFamily(
            f"{self.base_name}_session_detection_time_seconds",
            "Negotiated detection time",
            labels=LABELS,
        )
        transmit = GaugeMetricFamily(
            f"{self.base_name}_session_transmit_interval_seconds",
            "Negotiated transmit interval",
            labels=LABELS,
        )
        up_seconds = GaugeMetricFamily(
            f"{self.base_name}_session_up_seconds",
            "Seconds since the session came up",
            labels=LABELS,
        )
        info = InfoMetricFamily(
            f"{self.base_name}_session",
            "BFD session state and diagnostics on both ends",
            labels=LABELS,
        )
        for session in iter_items(reply, ("bfd-session",)):
            labels = [
                label(read.text(session, "session-neighbor")),
                label(read.text(session, "session-interface", required=False)),
                ",".join(
                    sorted(
                        label(text(client, "client-name"))
                        for client in findall(session, "bfd-client")
                    )
                ),
            ]
            state = read.text(session, "session-state")
            up.add_metric(labels, 1.0 if (state or "").lower() == "up" else 0.0)
            add(detection, labels, read.number(session, "session-detection-time"))
            add(
                transmit,
                labels,
                read.number(session, "session-transmission-interval"),
            )
            add(up_seconds, labels, read.seconds(session, "session-up-time", required=False))
            info.add_metric(
                labels,
                {
                    "state": label(state),
                    "remote_state": label(read.text(session, "remote-state", required=False)),
                    "local_diagnostic": label(
                        read.text(session, "local-diagnostic", required=False)
                    ),
                    "remote_diagnostic": label(
                        read.text(session, "remote-diagnostic", required=False)
                    ),
                },
            )
        yield from read.unique((up, detection, transmit, up_seconds, info))
