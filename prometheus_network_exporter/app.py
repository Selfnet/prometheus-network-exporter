import argparse
import getpass
import os
import signal
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Dict
import tornado.ioloop
import tornado.web
from fqdn import FQDN
from prometheus_client import exposition, generate_latest
from tornado.concurrent import run_on_executor

import prometheus_network_exporter.netstat as netstat
from prometheus_network_exporter import __version__ as VERSION
from prometheus_network_exporter.baseapp import Application
from prometheus_network_exporter.devices.basedevice import Device
from prometheus_network_exporter.devices.junosdevice import \
    JuniperNetworkDevice

if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")
SERVER = None
GLOBAL_GUARD: bool = False
CONNECTION_POOL: Dict[str, Device] = {}
COUNTER_DIR = '.tmp'
MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 60
MAX_WORKERS = 90


class MetricsHandler(tornado.web.RequestHandler):
    """
    Tornado ``Handler`` that serves prometheus metrics.
    """

    async def get_ssh_count(self):
        counts = Counter(tok['state'] for tok in [*netstat.ssh(v4=True), *netstat.ssh(v6=True)])
        for state, count in counts.items():
            self.application.CONNECTIONS.labels(state, 'ssh').set(count)

    async def get_http_count(self):
        counts = Counter(tok['state'] for tok in [*netstat.http(v4=True), *netstat.http(v6=True)])
        for state, count in counts.items():
            self.application.CONNECTIONS.labels(state, 'http').set(count)

    async def get_metrics(self):
        await self.get_ssh_count()
        await self.get_http_count()

    async def get(self):
        await self.get_metrics()
        _, content_type = exposition.choose_encoder(
            self.request.headers.get('Accept'))
        self.set_header('Content-Type', content_type)
        data = generate_latest(self.application.multiprocess_registry)
        self.write(data)


class ExporterHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    @run_on_executor
    def get_device_information(self, hostname):
        global CONNECTION_POOL
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
            #         elif module['device'] == 'arubaos':
            #             http = 'https' if module['auth'].get(
            #                 'http_secure', True) else 'http'
            #             port = module['auth'].get('port', 4343)
            #             dev = ArubaNetworkDevice(
            #                 hostname=hostname,
            #                 username=module['auth'].get(
            #                     'username', getpass.getuser()),
            #                 password=module['auth']['password'],
            #                 protocol=http,
            #                 port=port,
            #                 proxy=module['auth'].get(
            #                     'proxy'),
            #                 verify=module['auth'].get(
            #                     'verify', False)
            #             )
            #         elif module['device'] == 'airmax':
            #             http = 'https' if module['auth'].get(
            #                 'http_secure', True) else 'http'
            #             port = module['auth'].get('port', 443)
            #             dev = AirMaxDevice(
            #                 hostname=hostname,
            #                 username=module['auth'].get(
            #                     'username', getpass.getuser()),
            #                 password=module['auth']['password'],
            #                 protocol=http,
            #                 port=port,
            #                 proxy=module['auth'].get(
            #                     'proxy'),
            #                 verify=module['auth'].get(
            #                     'verify', False)
            #             )
                except KeyError as e:
                    raise e
                    return 500, 'ConfigError', "You must specify a password.".encode('utf8')
            CONNECTION_POOL[hostname] = dev
        dev = CONNECTION_POOL[hostname]
        if dev.lock.locked():
            return 500, "Ressource Locked", "{} is currently locked".format(hostname).encode('utf8')
        if not dev or not dev.device:
            del CONNECTION_POOL[hostname]
            return 500, 'ConnectionError', 'No Connection for {}, have done cleanup!'.format(hostname).encode('utf8')

        # get metrics from file
        return dev.collect()

    async def get(self):
        global CONNECTION_POOL, GLOBAL_GUARD
        self.set_header('Content-type', 'text/plain')
        hostname = self.get_argument('target')
        if GLOBAL_GUARD:
            self.set_status(503, reason="Service Unavailable Ressource blocked")
            self.write(bytes("{} is not a valid FQDN!".format(hostname).encode('utf8')))
            return
        if not FQDN(hostname).is_valid:
            self.set_status(409, reason="FQDN is invalid!")
            self.write(bytes("{} is not a valid FQDN!".format(hostname).encode('utf8')))
            return
        if hostname:
            if hostname not in CONNECTION_POOL.keys():
                CONNECTION_POOL[hostname] = None
            self.application.used_workers.inc()
            try:
                code, status, data = await self.get_device_information(
                    hostname=hostname)
            except Exception as e:
                print(f"{hostname} :: {e}")
                raise(e)
            finally:
                self.application.used_workers.dec()

        self.set_status(code, reason=status)
        self.write(data)


class AllDeviceReloadHandler(tornado.web.RequestHandler):

    async def get(self):
        code, status = await self.reload_all()
        self.set_status(code, reason=status)
        self.write(bytes(status, 'utf-8'))

    async def reload_all(self):
        global GLOBAL_GUARD, CONNECTION_POOL
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
            print("{} :: Connection Object {}".format(
                entry, "deleted" if entry not in CONNECTION_POOL.keys() else "what the f***"))
        GLOBAL_GUARD = False
        return 200, "Reloaded all!"


class DeviceReloadHandler(tornado.web.RequestHandler):

    async def reload_device(self, hostname):
        global CONNECTION_POOL
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
                print("{} :: Connection Object {}".format(
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


def app():
    global MAX_WORKERS, COUNTER_DIR
    parser = argparse.ArgumentParser(
        prog='prometheus-network-exporter',
        description="Prometheus exporter for JunOS switches and routers + Others")
    parser.add_argument('--version', action='version',
                        version='%(prog)s{}'.format(VERSION))
    parser.add_argument('--port', type=int, default=9332,
                        help="Specifys the port on which the exporter is running.(Default=9332)")
    parser.add_argument('--ip', type=str, default="::1",
                        help="Specifys the port on which the exporter is running.(Default=::1)")
    parser.add_argument(
        '--worker',
        type=int,
        default=10,
        help="Specifys the max concurrent threads running for the metrics collection. (Default=150)")
    os.makedirs(COUNTER_DIR, mode=0o755, exist_ok=True)
    args = parser.parse_args()
    urls = [
        (r'^/metrics$', MetricsHandler),
        (r'^/device$', ExporterHandler),
        (r'^/reload$', AllDeviceReloadHandler),
        (r'^/reload/(.*?)', DeviceReloadHandler)
    ]
    app = Application(urls, max_workers=args.worker, prometheus_buckets=[0.5, 1, 3, 5, 8, 13, 17, 21, 27, 34, 40, 55])
    MAX_WORKERS = app.max_workers
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    global SERVER
    SERVER = tornado.httpserver.HTTPServer(app)
    print("Listening on http://{}:{}".format(args.ip, args.port))
    SERVER.listen(args.port, address=args.ip)

    tornado.ioloop.IOLoop.current().start()
    print("Exiting ...")


def sig_handler(sig, frame):
    print('Caught signal: {}'.format(sig))
    tornado.ioloop.IOLoop.current().add_callback_from_signal(shutdown)


def shutdown():
    global SERVER, GLOBAL_GUARD
    GLOBAL_GUARD = True
    print('Stopping http server')
    for hostname, data in CONNECTION_POOL.items():
        try:
            data.lock.acquire()
            data.disconnect()
        except:
            pass
        print("{} :: Connection State {}".format(
            hostname, "Disconnected" if (
                not data or
                not data.is_connected()) else "Connected"))
    SERVER.stop()
    GLOBAL_GUARD = False
    exit(0)


if __name__ == "__main__":
    app()
