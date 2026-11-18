"""Worker processes behind one port: sharding and the forwarding front door."""

import tornado.testing
import tornado.web
from tornado.httpserver import HTTPServer
from tornado.netutil import bind_sockets

from prometheus_network_exporter.processes import ProxyApplication, shard_for


def test_shard_is_stable_and_spreads():
    hosts = [f"switch-{i}.lan.example.com" for i in range(200)]
    first = [shard_for(h, 4) for h in hosts]
    assert first == [shard_for(h, 4) for h in hosts]
    assert all(0 <= s < 4 for s in first)
    assert len(set(first)) == 4, "200 targets must use every one of 4 workers"
    assert shard_for("any.example.com", 1) == 0


class EchoHandler(tornado.web.RequestHandler):
    """Stands in for a worker: answers with its port and the request."""

    def get(self, hostname=None):
        port = self.application.settings["port"]
        if self.get_argument("module", "") == "broken":
            self.set_status(500, reason="ConnectionError")
            self.write(f"No Connection for {self.get_argument('target')}".encode())
            return
        if hostname is not None:
            self.set_status(409, reason="Busy")
            self.write(f"{hostname}: still scraping".encode())
            return
        self.set_header("Content-Type", "text/plain; version=0.0.4")
        self.write(f"port={port} uri={self.request.uri}".encode())


def fake_worker():
    sockets = bind_sockets(0, "127.0.0.1")
    port = sockets[0].getsockname()[1]
    app = tornado.web.Application(
        [(r"^/device$", EchoHandler), (r"^/unlock/(.*?)$", EchoHandler)], port=port
    )
    server = HTTPServer(app)
    server.add_sockets(sockets)
    return server, port


class ProxyTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        self.servers = []
        self.ports = []
        for _ in range(2):
            server, port = fake_worker()
            self.servers.append(server)
            self.ports.append(port)
        self.closed_port = bind_sockets(0, "127.0.0.1")[0].getsockname()[1]
        return ProxyApplication(self.ports, max_clients=20)

    def tearDown(self):
        for server in self.servers:
            server.stop()
        super().tearDown()

    def _device(self, target, module="core"):
        return self.fetch(f"/device?target={target}&module={module}", raise_error=False)

    def test_target_always_reaches_its_own_worker(self):
        targets = [f"core-{i}.lan.example.com" for i in range(12)]
        seen = {}
        for target in targets:
            response = self._device(target)
            assert response.code == 200
            port = int(response.body.decode().split()[0].split("=")[1])
            assert port == self.ports[shard_for(target, 2)]
            seen.setdefault(port, []).append(target)
            assert self._device(target).body == response.body, "second request must hit the same worker"
        assert len(seen) == 2
        assert response.headers["Content-Type"].startswith("text/plain")

    def test_status_and_body_pass_through(self):
        response = self._device("core-1.lan.example.com", module="broken")
        assert response.code == 500
        assert response.reason == "ConnectionError"
        assert b"No Connection for core-1.lan.example.com" in response.body
        response = self.fetch("/unlock/core-1.lan.example.com", raise_error=False)
        assert response.code == 409
        assert b"still scraping" in response.body

    def test_dead_worker_gives_502(self):
        self._app.ports = [self.closed_port, self.closed_port]
        response = self._device("core-1.lan.example.com")
        assert response.code == 502
        assert b"worker process did not answer" in response.body

    def test_metrics_served_by_the_front_door(self):
        response = self.fetch("/metrics")
        assert response.code == 200
