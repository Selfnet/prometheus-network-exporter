from __future__ import annotations

import logging
from threading import Lock
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:  # the import pulls in prometheus_client; app.py sets its env first
    from prometheus_network_exporter.devices.basedevice import Device

__version__ = "1.4.2"

GLOBAL_GUARD: Lock = Lock()
CONNECTION_POOL: Dict[str, "Device"] = {}
COUNTER_DIR = ".tmp"
MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 60
MAX_WORKERS = 90

APP_LOGGER = logging.getLogger("network_exporter")
APP_LOGGER.setLevel(logging.INFO)
