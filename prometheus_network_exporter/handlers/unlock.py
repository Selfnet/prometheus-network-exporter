import tornado
from fqdn import FQDN

from prometheus_network_exporter import CONNECTION_POOL, APP_LOGGER


class DeviceUnlockHandler(tornado.web.RequestHandler):

    async def unlock(self, hostname):
        global CONNECTION_POOL, APP_LOGGER
        if FQDN(hostname).is_valid:
            if hostname in CONNECTION_POOL.keys() and CONNECTION_POOL[hostname] is not None:
                try:
                    CONNECTION_POOL[hostname].lock.acquire(True)
                    CONNECTION_POOL[hostname].disconnect()
                finally:
                    CONNECTION_POOL[hostname].lock.release()
                    del CONNECTION_POOL[hostname]
                APP_LOGGER.info(f"{hostname} :: Connection Object deleted")
                return 200, 'Deleted!', f"{hostname} got deleted!"
            else:
                return 404, 'Element not Found', f"{hostname} is locked or not found."
        else:
            return 409, "FQDN is invalid!", f"{hostname} is not a valid FQDN!"

    async def get(self, hostname):
        code, status, data = await self.unlock(hostname=hostname)
        self.set_status(code, reason=status)
        self.write(bytes(data, 'utf-8'))
