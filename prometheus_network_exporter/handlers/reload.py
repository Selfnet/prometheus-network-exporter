import tornado
from fqdn import FQDN

from prometheus_network_exporter import CONNECTION_POOL, GLOBAL_GUARD, APP_LOGGER


class AllDeviceReloadHandler(tornado.web.RequestHandler):

    async def get(self):
        code, status = await self.reload_all()
        self.set_status(code, reason=status)
        self.write(bytes(status, 'utf-8'))

    async def reload_all(self):
        global GLOBAL_GUARD, CONNECTION_POOL, APP_LOGGER
        GLOBAL_GUARD = True
        entries = list(CONNECTION_POOL.keys())
        for entry in entries:
            try:
                CONNECTION_POOL[entry].lock.acquire()
                CONNECTION_POOL[entry].disconnect()
            except:
                pass
            finally:
                CONNECTION_POOL[entry].lock.release()
                del CONNECTION_POOL[entry]
            APP_LOGGER.info("{} :: Connection Object {}".format(
                entry, "deleted" if entry not in CONNECTION_POOL.keys() else "what the f***"))
        GLOBAL_GUARD = False
        return 200, "Reloaded all!"


class DeviceReloadHandler(tornado.web.RequestHandler):

    async def reload_device(self, hostname):
        global CONNECTION_POOL, APP_LOGGER
        if FQDN(hostname).is_valid:
            if hostname in CONNECTION_POOL.keys():
                try:
                    CONNECTION_POOL[hostname].lock.acquire()
                    CONNECTION_POOL[hostname].disconnect()
                except:
                    pass
                finally:
                    CONNECTION_POOL[hostname].lock.release()
                    del CONNECTION_POOL[hostname]
                APP_LOGGER.info("{} :: Connection Object {}".format(
                    hostname, "deleted" if hostname not in CONNECTION_POOL.keys() else "what the f***"))
                return 200, 'Deleted!', "{} got deleted!".format(
                    hostname)
            else:
                return 404, 'Element not Found or Locked!', "{} is locked or not found.".format(
                    hostname)
        else:
            return 409, "FQDN is invalid!", "{} is not a valid FQDN!".format(
                hostname)

    async def get(self, hostname):
        code, status, data = await self.reload_device(hostname=hostname)
        self.set_status(code, reason=status)
        self.write(bytes(data, 'utf-8'))
