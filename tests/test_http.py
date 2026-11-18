"""The HTTP side: application setup, /device, /unlock, /metrics, /memstats and app()."""

import os
import pathlib
import threading
import tracemalloc
from unittest import mock

import pytest
import tornado.testing

from prometheus_network_exporter import CONNECTION_POOL, COUNTER_DIR, GLOBAL_GUARD
from prometheus_network_exporter import app as app_module
from prometheus_network_exporter import processes
from prometheus_network_exporter.baseapp import Application
from prometheus_network_exporter.handlers import device as device_handler
from prometheus_network_exporter.handlers import unlock
from prometheus_network_exporter.handlers.device import ExporterHandler
from prometheus_network_exporter.handlers.metrics import MetricsHandler
from prometheus_network_exporter.handlers.tracemalloc import TraceMallocHandler
from prometheus_network_exporter.handlers.unlock import DeviceUnlockHandler

CONFIG = pathlib.Path(__file__).parent.parent / "prometheus_network_exporter" / "config" / "config.yml"
TARGET = "core-1.example.net"


class FakeDevice:
    """Stands in for JuniperNetworkDevice in the connection pool."""

    instances = []

    def __init__(self, hostname, **kwargs):
        self.hostname = hostname
        self.kwargs = kwargs
        self.device = object()
        self.lock = threading.Lock()
        self.disconnected = False
        FakeDevice.instances.append(self)

    def collect(self):
        return 200, "OK", f"metrics of {self.hostname}".encode()

    def disconnect(self):
        self.disconnected = True


def build(debug=False):
    # app() creates the counter directory before it builds the application.
    os.makedirs(COUNTER_DIR, exist_ok=True)
    return Application(
        [
            (r"^/metrics$", MetricsHandler),
            (r"^/device$", ExporterHandler),
            (r"^/unlock/(.*?)", DeviceUnlockHandler),
            (r"^/memstats$", TraceMallocHandler),
        ],
        max_workers=4,
        prometheus_buckets=[1, 5],
        debug=debug,
        config_path=str(CONFIG),
    )


class HandlerTest(tornado.testing.AsyncHTTPTestCase):
    debug = False

    def get_app(self):
        return build(self.debug)

    def setUp(self):
        super().setUp()
        CONNECTION_POOL.clear()
        FakeDevice.instances.clear()
        patcher = mock.patch.object(device_handler, "JuniperNetworkDevice", FakeDevice)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(CONNECTION_POOL.clear)

    def get(self, path):
        return self.fetch(path, raise_error=False)


class DeviceHandlerTest(HandlerTest):
    def test_scrape_creates_one_pool_entry_per_module(self):
        response = self.get(f"/device?target={TARGET}&module=core_fast")
        assert response.code == 200
        assert response.body == f"metrics of {TARGET}".encode()
        self.get(f"/device?target={TARGET}&module=core_fast")
        self.get(f"/device?target={TARGET}&module=core_slow")
        assert sorted(CONNECTION_POOL) == [f"{TARGET}|core_fast", f"{TARGET}|core_slow"]
        assert len(FakeDevice.instances) == 2
        options = FakeDevice.instances[1].kwargs["options"]
        assert options["optics_interval_seconds"] == 0
        assert options["tables"] == ["inet.0", "inet6.0"]

    def test_missing_and_unknown_module(self):
        assert self.get(f"/device?target={TARGET}").code == 404
        response = self.get(f"/device?target={TARGET}&module=nope")
        assert response.code == 404
        assert b"Available modules" in response.body
        assert CONNECTION_POOL == {}

    def test_invalid_target(self):
        assert self.get("/device?target=not_a_host!&module=default").code == 409
        assert self.get("/device?module=default").code == 400

    def test_no_connection_drops_the_pool_entry(self):
        def unreachable(hostname, **kwargs):
            device = FakeDevice(hostname, **kwargs)
            device.device = None
            return device

        with mock.patch.object(device_handler, "JuniperNetworkDevice", unreachable):
            response = self.get(f"/device?target={TARGET}&module=default")
        assert response.code == 500
        assert CONNECTION_POOL == {}

    def test_password_auth(self):
        self._app.CONFIG["pw"] = {**self._app.CONFIG["default"],
                                  "auth": {"method": "password", "username": "u", "password": "p"}}
        assert self.get(f"/device?target={TARGET}&module=pw").code == 200
        assert FakeDevice.instances[0].kwargs["password"] == "p"

    def test_shutdown_guard_blocks_scrapes(self):
        GLOBAL_GUARD.acquire()
        try:
            assert self.get(f"/device?target={TARGET}&module=default").code == 503
        finally:
            GLOBAL_GUARD.release()

    def test_request_duration_is_recorded(self):
        self.get(f"/device?target={TARGET}&module=default")
        samples = self._app.request_time_histogram.collect()[0].samples
        assert any(s.labels.get("path", "").startswith("/device") for s in samples)


class UnlockTest(HandlerTest):
    def test_unlock_disconnects_every_module(self):
        self.get(f"/device?target={TARGET}&module=core_fast")
        self.get(f"/device?target={TARGET}&module=core_slow")
        response = self.get(f"/unlock/{TARGET}")
        assert response.code == 200
        assert CONNECTION_POOL == {}
        assert all(device.disconnected for device in FakeDevice.instances)

    def test_unknown_and_invalid_target(self):
        assert self.get(f"/unlock/{TARGET}").code == 404
        assert self.get("/unlock/not_a_host!").code == 409

    def test_busy_device_is_kept(self):
        self.get(f"/device?target={TARGET}&module=default")
        device = CONNECTION_POOL[f"{TARGET}|default"]
        device.lock.acquire()
        try:
            with mock.patch.object(unlock, "UNLOCK_TIMEOUT_SECONDS", 0.01):
                response = self.get(f"/unlock/{TARGET}")
        finally:
            device.lock.release()
        assert response.code == 409
        assert f"{TARGET}|default" in CONNECTION_POOL


class MetricsTest(HandlerTest):
    def test_metrics_include_tcp_states_and_workers(self):
        connections = [{"state": "ESTABLISHED"}, {"state": "ESTABLISHED"}, {"state": "TIME_WAIT"}]
        with mock.patch("prometheus_network_exporter.netstat.netstat", return_value=iter([])), \
                mock.patch("prometheus_network_exporter.netstat.ssh", side_effect=[iter(connections), iter([])]), \
                mock.patch("prometheus_network_exporter.netstat.http", side_effect=[iter([]), iter([])]):
            response = self.get("/metrics")
        assert response.code == 200
        state = self._app.CONNECTIONS.labels("ESTABLISHED", "ssh")._value.get()
        assert state == 2

    def test_memstats_only_in_debug(self):
        assert self.get("/memstats").code == 404


class DebugTest(HandlerTest):
    debug = True

    def test_memstats(self):
        tracemalloc.start()
        try:
            response = self.get("/memstats?limit=3")
            assert response.code == 200
            assert response.body.startswith(b"Top 3 lines")
            assert b"Total allocated size" in response.body
        finally:
            tracemalloc.stop()


def test_application_rejects_an_invalid_config(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text("default:\n  device: junos\n  auth: {method: ssh_key}\n  metrics: [nonsense]\n")
    with pytest.raises(Exception):
        Application([], config_path=str(config))


def run_app(monkeypatch, *args):
    monkeypatch.setattr("sys.argv", ["prometheus-network-exporter", "--config", str(CONFIG), *args])
    server = mock.Mock()
    loop = mock.Mock()
    monkeypatch.setattr(app_module.tornado.httpserver, "HTTPServer", mock.Mock(return_value=server))
    monkeypatch.setattr(app_module.tornado.ioloop.IOLoop, "current", mock.Mock(return_value=loop))
    monkeypatch.setattr(app_module.signal, "signal", mock.Mock())
    serve = mock.Mock()
    monkeypatch.setattr(processes, "serve", serve)
    app_module.app()
    return server, loop, serve


def test_app_single_process(monkeypatch):
    server, loop, serve = run_app(monkeypatch, "--port", "19332", "--ip", "127.0.0.1", "--worker", "3")
    server.listen.assert_called_once_with(19332, address="127.0.0.1")
    loop.start.assert_called_once()
    serve.assert_not_called()
    assert app_module.MAX_WORKERS == 3


def test_app_hands_several_processes_to_the_front_door(monkeypatch):
    server, loop, serve = run_app(monkeypatch, "--processes", "2")
    serve.assert_called_once()
    args, build_application = serve.call_args[0]
    assert args.processes == 2
    assert isinstance(build_application(), Application)
    server.listen.assert_not_called()


def test_shutdown_disconnects_idle_devices(monkeypatch):
    CONNECTION_POOL.clear()
    idle, busy, failing = FakeDevice("a.example.net"), FakeDevice("b.example.net"), FakeDevice("c.example.net")
    failing.disconnect = mock.Mock(side_effect=RuntimeError("gone"))
    # Still scraping: the lock is not free within the timeout.
    busy.lock = mock.Mock(**{"acquire.return_value": False})
    CONNECTION_POOL.update({"a|m": idle, "b|m": busy, "c|m": failing, "d|m": None})
    monkeypatch.setattr(app_module.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(app_module, "SERVER", mock.Mock())
    try:
        with pytest.raises(SystemExit):
            app_module.shutdown()
    finally:
        CONNECTION_POOL.clear()
    assert idle.disconnected and not busy.disconnected
    assert not failing.lock.locked() and not GLOBAL_GUARD.locked()
    app_module.SERVER.stop.assert_called_once()


def test_signal_schedules_the_shutdown(monkeypatch):
    loop = mock.Mock()
    monkeypatch.setattr(app_module.tornado.ioloop.IOLoop, "current", mock.Mock(return_value=loop))
    app_module.sig_handler(15, None)
    loop.add_callback_from_signal.assert_called_once_with(app_module.shutdown)


def test_clear_counter_dir(tmp_path):
    (tmp_path / "counter_1.db").write_text("x")
    (tmp_path / "keep.txt").write_text("x")
    processes.clear_counter_dir(str(tmp_path))
    assert sorted(os.listdir(tmp_path)) == ["keep.txt"]
