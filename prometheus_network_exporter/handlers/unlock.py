import tornado
from fqdn import FQDN

from prometheus_network_exporter import CONNECTION_POOL, APP_LOGGER

# How long /unlock waits for a running scrape before giving up.
UNLOCK_TIMEOUT_SECONDS = 10


def unlock_device(hostname: str, module: str | None = None) -> tuple:
    """Disconnect and drop the pool entries of the target, one per module.

    With a module only that module's session is dropped, the next scrape of
    that module logs in again. Runs in a worker thread: waiting for the
    device lock on the IOLoop thread would stall every other request.
    """
    keys = [
        key
        for key, device in list(CONNECTION_POOL.items())
        if device is not None
        and key.split("|", 1)[0] == hostname
        and (module is None or key.split("|", 1)[1] == module)
    ]
    if not keys:
        scope = f"{hostname} with module {module}" if module else hostname
        return 404, "Element not Found", f"{scope} is locked or not found."
    busy = []
    for key in keys:
        device = CONNECTION_POOL.get(key)
        if device is None:
            continue
        if not device.lock.acquire(timeout=UNLOCK_TIMEOUT_SECONDS):
            busy.append(key)
            continue
        try:
            device.disconnect()
        finally:
            device.lock.release()
            CONNECTION_POOL.pop(key, None)
    APP_LOGGER.info(f"{hostname} :: Connection Objects deleted, still busy: {busy}")
    if busy:
        return 409, "Busy", f"{hostname}: still scraping {busy}, try again."
    return 200, "Deleted!", f"{hostname} got deleted!"


class DeviceUnlockHandler(tornado.web.RequestHandler):
    async def get(self, hostname):
        if FQDN(hostname).is_valid:
            module = self.get_argument("module", None)
            code, status, data = await tornado.ioloop.IOLoop.current().run_in_executor(
                None, unlock_device, hostname, module
            )
        else:
            code, status, data = 409, "FQDN is invalid!", f"{hostname} is not a valid FQDN!"
        self.set_status(code, reason=status)
        self.write(bytes(data, "utf-8"))
