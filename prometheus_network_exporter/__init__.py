import logging
from typing import Dict

from prometheus_network_exporter.devices.basedevice import Device

__version__ = "1.0.3"
# global APP_LOGGER, CONNECTION_POOL, COUNTER_DIR, MAX_WAIT_SECONDS_BEFORE_SHUTDOWN, MAX_WORKERS

GLOBAL_GUARD: bool = False
CONNECTION_POOL: Dict[str, Device] = {}
COUNTER_DIR = '.tmp'
MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 60
MAX_WORKERS = 90

APP_LOGGER = logging.getLogger("network_exporter")
APP_LOGGER.setLevel(logging.INFO)


