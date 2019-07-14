import os
import sys
import getpass
import signal
import argparse
import threading
import tornado.ioloop
import tornado.web
from collections import Counter
from fqdn import FQDN
from prometheus_client import exposition
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from prometheus_client import generate_latest
from prometheus_network_exporter import __version__ as VERSION
from prometheus_network_exporter.baseapp import Application
from prometheus_network_exporter.registry import Metrics
from prometheus_network_exporter.devices.junosdevice import JuniperNetworkDevice, JuniperMetrics
from prometheus_network_exporter.devices.arubadevice import ArubaNetworkDevice, ArubaMetrics
from prometheus_network_exporter.devices.ubntdevice import AirMaxDevice, AirMaxMetrics
from prometheus_network_exporter.devices.ciscodevice import CiscoMetrics
import prometheus_network_exporter.netstat as netstat
if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

CONNECTION_POOL = {}
MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 60
MAX_WORKERS = 90
SERVER = None
COUNTER_DIR = '.tmp'


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

    def initialize(self):
        self.collectors = {
            'junos': JuniperMetrics(exception_counter=self.application.exception_counter),
            'arubaos': ArubaMetrics(exception_counter=self.application.exception_counter),
            'ios': CiscoMetrics(exception_counter=self.application.exception_counter),
            'airmax': AirMaxMetrics(exception_counter=self.application.exception_counter)
        }

    @run_on_executor
    def get_device_information(self, hostname, lock):
        try:
            module = self.application.CONFIG[self.get_argument('module')]
        except tornado.web.MissingArgumentError:
            return 404, "you're holding it wrong!", \
                """you're holding it wrong!:
                {}
                /metrics?module=default&target=target.example.com""".format(
                    self.request.uri)
        except KeyError:
            return 404, "Wrong module!", "you're holding it wrong!:\nAvailable modules are: {}".format(
                list(self.application.CONFIG.keys()))

        if (
            not CONNECTION_POOL[hostname] or
            not CONNECTION_POOL[hostname].get('device')
        ):
            CONNECTION_POOL[hostname] = {}
            dev = None
            if module['auth']['method'] == 'ssh_key':
                # using ssh key
                if module['device'] == 'junos':
                    dev = JuniperNetworkDevice(hostname=hostname,
                                               user=module['auth'].get(
                                                   'username', getpass.getuser()),
                                               ssh_private_key_file=module['auth'].get(
                                                   'ssh_key', None),
                                               port=module['auth'].get(
                                                   'port', 22),
                                               ssh_config=module['auth'].get(
                                                   'ssh_config', None),
                                               password=module['auth'].get('password', None))
            elif module['auth']['method'] == 'password':
                try:
                    if module['device'] == 'arubaos':

                        http = 'https' if module['auth'].get(
                            'http_secure', True) else 'http'
                        port = module['auth'].get('port', 4343)
                        dev = ArubaNetworkDevice(
                            hostname=hostname,
                            username=module['auth'].get(
                                'username', getpass.getuser()),
                            password=module['auth']['password'],
                            protocol=http,
                            port=port,
                            proxy=module['auth'].get(
                                'proxy'),
                            verify=module['auth'].get(
                                'verify', False)
                        )
                    elif module['device'] == 'junos':
                        dev = JuniperNetworkDevice(
                            hostname=hostname,
                            user=module['auth'].get(
                                'username', getpass.getuser()),
                            password=module['auth']['password'],
                            port=module['auth'].get('port', 22)
                        )
                    elif module['device'] == 'airmax':
                        http = 'https' if module['auth'].get(
                            'http_secure', True) else 'http'
                        port = module['auth'].get('port', 443)
                        dev = AirMaxDevice(
                            hostname=hostname,
                            username=module['auth'].get(
                                'username', getpass.getuser()),
                            password=module['auth']['password'],
                            protocol=http,
                            port=port,
                            proxy=module['auth'].get(
                                'proxy'),
                            verify=module['auth'].get(
                                'verify', False)
                        )
                except KeyError:
                    return 500, 'Config Error', "You must specify a password."
            CONNECTION_POOL[hostname]['device'] = dev
        dev = CONNECTION_POOL[hostname]['device']
        if not dev or not dev.device:
            del CONNECTION_POOL[hostname]
            return 500, 'No Connection for {}, have done cleanup!'.format(hostname)

        # get metrics from file
        types = module['metrics']
        lock.acquire()
        data = self.collectors[module['device']].metrics(types, dev, Metrics())
        lock.release()
        return data

    async def get(self):
        self.set_header('Content-type', 'text/plain')
        hostname = self.get_argument('target')
        if not FQDN(hostname).is_valid:
            self.set_status(409, reason="FQDN is invalid!")
            self.write(bytes("{} is not a valid FQDN!".format(hostname)))
            return
        if hostname:
            if hostname not in CONNECTION_POOL.keys():
                CONNECTION_POOL[hostname] = {}
                CONNECTION_POOL[hostname]['lock'] = threading.Lock()

            self.application.used_workers.inc()
            try:
                code, status, data = await self.get_device_information(
                    hostname=hostname,
                    lock=CONNECTION_POOL[hostname]['lock']
                )
            except Exception as e:
                raise(e)
            finally:
                self.application.used_workers.dec()

        self.set_status(code, reason=status)
        self.write(bytes(data, 'utf-8'))


class AllDeviceReloadHandler(tornado.web.RequestHandler):

    async def get(self):
        code, status = await self.reload_all()
        self.set_status(code, reason=status)
        self.write(bytes(status, 'utf-8'))

    async def reload_all(self):
        entries = list(CONNECTION_POOL.keys())
        for entry in entries:
            if entry in CONNECTION_POOL.keys():
                lock = CONNECTION_POOL[entry]['lock']
                lock.acquire()
                try:
                    CONNECTION_POOL[entry]['device'].disconnect()
                except:
                    pass
                finally:
                    lock.release()
                    CONNECTION_POOL[entry]['lock'] = lock
                del CONNECTION_POOL[entry]
                print("{} :: Connection Object {}".format(
                    entry, "deleted" if entry not in CONNECTION_POOL.keys() else "what the f***"))
        return 200, "Reloaded all!"


class DeviceReloadHandler(tornado.web.RequestHandler):

    async def reload_device(self, hostname):
        if FQDN(hostname).is_valid:
            if hostname in CONNECTION_POOL.keys:
                lock = CONNECTION_POOL[hostname]['lock']
                lock.acquire()
                try:
                    CONNECTION_POOL[hostname]['device'].disconnect()
                except:
                    pass
                finally:
                    lock.release()
                    CONNECTION_POOL[hostname]['lock'] = lock
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
    global MAX_WORKERS
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
    print('Stopping http server')
    for hostname, data in CONNECTION_POOL.items():
        lock = data['lock']
        lock.acquire()
        try:
            data['device'].disconnect()
        except:
            pass
        finally:
            lock.release()
            data['lock'] = lock
        print("{} :: Connection State {}".format(
            hostname, "Disconnected" if (
                not data.get('device') or
                not data['device'].is_connected()) else "Connected"))
    SERVER.stop()
    exit(0)


if __name__ == "__main__":
    app()
