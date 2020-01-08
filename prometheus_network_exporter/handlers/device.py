import getpass
from concurrent.futures import ThreadPoolExecutor

import tornado
from fqdn import FQDN

from prometheus_network_exporter import (APP_LOGGER, CONNECTION_POOL,
                                         MAX_WORKERS, GLOBAL_GUARD)
from prometheus_network_exporter.devices.junosdevice import \
    JuniperNetworkDevice


class ExporterHandler(tornado.web.RequestHandler):
    global MAX_WORKERS
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    @tornado.concurrent.run_on_executor
    def get_device_information(self, hostname):
        global CONNECTION_POOL, APP_LOGGER
        try:
            module = self.application.CONFIG[self.get_argument('module')]
        except tornado.web.MissingArgumentError:
            return 404, "you're holding it wrong!", \
                """you're holding it wrong!:
                {}
                /metrics?module=default&target=target.example.com""".format(
                    self.request.uri).encode("utf8")
        except KeyError:
            return 404, "Wrong module!", "you're holding it wrong!:\nAvailable modules are: {}".format(
                list(self.application.CONFIG.keys())).encode('utf8')

        if CONNECTION_POOL.get(hostname) is None:
            dev = None
            if module['auth']['method'] == 'ssh_key':
                # using ssh key
                if module['device'] == 'junos':
                    dev = JuniperNetworkDevice(
                        hostname=hostname,
                        user=module['auth'].get(
                            'username', getpass.getuser()),
                        ssh_private_key_file=module['auth'].get(
                            'ssh_key', None),
                        port=module['auth'].get(
                            'port', 22),
                        ssh_config=module['auth'].get(
                            'ssh_config', None),
                        password=module['auth'].get('password', None),
                        types=module['metrics'],
                        exception_counter=self.application.exception_counter
                    )
            elif module['auth']['method'] == 'password':
                try:
                    if module['device'] == 'junos':
                        dev = JuniperNetworkDevice(
                            hostname=hostname,
                            user=module['auth'].get(
                                'username', getpass.getuser()),
                            password=module['auth']['password'],
                            port=module['auth'].get('port', 22),
                            types=module['metrics'],
                            exception_counter=self.application.exception_counter
                        )
                except KeyError as e:
                    raise e
                    APP_LOGGER.info(e)
                    return 500, 'ConfigError', "You must specify a password.".encode('utf8')
            CONNECTION_POOL[hostname] = dev
        dev = CONNECTION_POOL[hostname]
        if dev.lock.locked():
            APP_LOGGER.info("Device is locked")
            return 500, "Ressource Locked", f"{hostname} is currently locked".encode('utf8')
        if not dev or not dev.device:
            del CONNECTION_POOL[hostname]
            return 500, 'ConnectionError', f'No Connection for {hostname}, have done cleanup!'.encode('utf8')

        # get metrics from file
        return dev.collect()

    async def get(self):
        global CONNECTION_POOL, GLOBAL_GUARD
        self.set_header('Content-type', 'text/plain')
        hostname = self.get_argument('target')
        if GLOBAL_GUARD:
            self.set_status(503, reason="Service Unavailable Ressource blocked")
            self.write(bytes(f"{hostname} is not a valid FQDN!".encode('utf8')))
            return
        if not FQDN(hostname).is_valid:
            self.set_status(409, reason="FQDN is invalid!")
            self.write(bytes(f"{hostname} is not a valid FQDN!".encode('utf8')))
            return
        if hostname:
            if hostname not in CONNECTION_POOL.keys():
                CONNECTION_POOL[hostname] = None
            self.application.used_workers.inc()
            try:
                code, status, data = await self.get_device_information(
                    hostname=hostname)
            except Exception as e:
                APP_LOGGER.info(f"{hostname} :: {e}")
            finally:
                self.application.used_workers.dec()

        self.set_status(code, reason=status)
        self.write(data)
