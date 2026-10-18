import getpass
import threading
from concurrent.futures import ThreadPoolExecutor
from paramiko import RSAKey

import tornado
from fqdn import FQDN
from prometheus_network_exporter import (
    APP_LOGGER,
    CONNECTION_POOL,
    GLOBAL_GUARD,
    MAX_WORKERS,
)
from prometheus_network_exporter.devices.junosdevice import JuniperNetworkDevice


# Serialises get-or-create of pool entries; two concurrent first scrapes of
# one target and module would otherwise create two device objects whose
# separate locks no longer serialise the scrapes.
POOL_LOCK = threading.Lock()


class ExporterHandler(tornado.web.RequestHandler):
    global MAX_WORKERS
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    @staticmethod
    def pool_key(hostname: str, module_name) -> str:
        """One device object per target and module.

        Each module registers its own collectors, so a target scraped with
        two modules (for example a fast and a slow one) needs two objects.
        """
        return f"{hostname}|{module_name}"

    @tornado.concurrent.run_on_executor
    def get_device_information(self, hostname, key):
        global CONNECTION_POOL, APP_LOGGER
        try:
            module = self.application.CONFIG[self.get_argument("module")]
        except tornado.web.MissingArgumentError:
            return (
                404,
                "you're holding it wrong!",
                """you're holding it wrong!:
                {}
                /metrics?module=default&target=target.example.com""".format(
                    self.request.uri
                ).encode(
                    "utf8"
                ),
            )
        except KeyError:
            return (
                404,
                "Wrong module!",
                "you're holding it wrong!:\nAvailable modules are: {}".format(
                    list(self.application.CONFIG.keys())
                ).encode("utf8"),
            )

        with POOL_LOCK:
            dev = self._device(hostname, key, module)
            if not dev or not dev.device:
                CONNECTION_POOL.pop(key, None)
                return (
                    500,
                    "ConnectionError",
                    f"No Connection for {hostname}, have done cleanup!".encode("utf8"),
                )
        # Outside the pool lock: the device lock serialises scrapes of one
        # target and module, other targets must not wait for this one.
        return dev.collect()

    def _device(self, hostname, key, module):
        options = {**module.get("routing", {}), **module.get("junos", {})}
        if CONNECTION_POOL.get(key) is None:
            dev = None
            if module["auth"]["method"] == "ssh_key":
                # using ssh key
                if module["device"] == "junos":
                    dev = JuniperNetworkDevice(
                        hostname=hostname,
                        user=module["auth"].get("username", getpass.getuser()),
                        ssh_private_key_file=module["auth"].get("ssh_key", None),
                        port=module["auth"].get("port", 22),
                        ssh_config=module["auth"].get("ssh_config", None),
                        password=module["auth"].get("password", None),
                        types=module["metrics"],
                        exception_counter=self.application.exception_counter,
                        options=options,
                    )
            elif module["auth"]["method"] == "password":
                try:
                    if module["device"] == "junos":
                        dev = JuniperNetworkDevice(
                            hostname=hostname,
                            user=module["auth"].get("username", getpass.getuser()),
                            password=module["auth"]["password"],
                            port=module["auth"].get("port", 22),
                            types=module["metrics"],
                            exception_counter=self.application.exception_counter,
                            options=options,
                        )
                except KeyError as e:
                    raise e
                    return (
                        500,
                        "ConfigError",
                        "You must specify a password.".encode("utf8"),
                    )
            CONNECTION_POOL[key] = dev
        return CONNECTION_POOL[key]

    async def get(self):
        global CONNECTION_POOL, GLOBAL_GUARD
        self.set_header("Content-type", "text/plain")

        hostname = self.get_argument("target")
        if GLOBAL_GUARD.locked():
            self.set_status(503, reason="Service Unavailable Service blocked")
            self.write(
                bytes(f"{hostname} GLOBAL_GUARD active Shutdown!".encode("utf8"))
            )
            return
        if not FQDN(hostname).is_valid:
            self.set_status(409, reason="FQDN is invalid!")
            self.write(bytes(f"{hostname} is not a valid FQDN!".encode("utf8")))
            return
        if hostname:
            # The entry is created only for a valid module, inside
            # get_device_information; unknown modules never enter the pool.
            key = self.pool_key(hostname, self.get_argument("module", None))
            self.application.used_workers.inc()
            try:
                code, status, data = await self.get_device_information(
                    hostname=hostname, key=key
                )
            except Exception as e:
                APP_LOGGER.info(f"{hostname} :: {e} {e.__traceback__}")
                raise e
            finally:
                self.application.used_workers.dec()

        self.set_status(code, reason=status)
        self.write(data)
