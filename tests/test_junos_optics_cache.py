import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from prometheus_network_exporter.collectors.junos.optics_cache import OpticsCache
from prometheus_network_exporter.collectors.junos.status import StatusCollector
from prometheus_network_exporter.devices.junosdevice import JuniperNetworkDevice


class OpticsCacheTests(unittest.TestCase):
    def setUp(self):
        self.clock = patch('prometheus_network_exporter.collectors.junos.optics_cache.time.monotonic')
        self.now = self.clock.start()
        self.now.return_value = 1000
        self.addCleanup(self.clock.stop)
        self.cache = OpticsCache()
        self.fetch = Mock(return_value=object())
        self.rpc = 'get_interface_optics_diagnostics_information'

    def test_reuses_then_refreshes_at_expiry(self):
        first = self.cache.reply(self.rpc, {}, self.fetch)
        self.now.return_value = 1299
        self.assertIs(self.cache.reply(self.rpc, {}, self.fetch), first)
        self.fetch.assert_called_once()
        self.now.return_value = 1300
        self.cache.reply(self.rpc, {}, self.fetch)
        self.assertEqual(self.fetch.call_count, 2)

    def test_interface_calls_are_never_cached_across_scrapes(self):
        for _ in range(2):
            self.cache.reply('get_interface_information', {'terse': True}, self.fetch)
        self.assertEqual(self.fetch.call_count, 2)
        self.assertEqual(self.cache.entries, {})

    def test_failed_refresh_drops_expired_value(self):
        self.cache.reply(self.rpc, {}, self.fetch)
        self.now.return_value = 1300
        self.fetch.return_value = None
        self.assertIsNone(self.cache.reply(self.rpc, {}, self.fetch))
        self.assertEqual(self.cache.entries, {})
        self.fetch.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError):
            self.cache.reply(self.rpc, {}, self.fetch)
        self.assertEqual(self.cache.entries, {})

    def test_pic_and_target_caches_are_independent(self):
        self.cache.reply('get_pic_detail', {'fpc_slot': '0', 'pic_slot': '1'}, self.fetch)
        self.cache.reply('get_pic_detail', {'fpc_slot': '0', 'pic_slot': '2'}, self.fetch)
        OpticsCache().reply('get_pic_detail', {'fpc_slot': '0', 'pic_slot': '1'}, self.fetch)
        self.assertEqual(self.fetch.call_count, 3)

    def test_zero_disables_cache(self):
        cache = OpticsCache(0)
        for _ in range(2):
            cache.reply(self.rpc, {}, self.fetch)
        self.assertEqual(self.fetch.call_count, 2)
        self.assertEqual(cache.entries, {})

    def test_device_wrapper_uses_the_optics_cache(self):
        device = Mock(spec=JuniperNetworkDevice)
        device.optics_cache = self.cache
        for _ in range(2):
            JuniperNetworkDevice.rpc_reply(device, self.rpc)
        device._rpc_reply.assert_called_once_with(self.rpc)
        for _ in range(2):
            JuniperNetworkDevice.rpc_reply(device, 'get_interface_information')
        self.assertEqual(device._rpc_reply.call_count, 3)

    def test_source_age_and_refresh_timestamp(self):
        with patch('prometheus_network_exporter.collectors.junos.optics_cache.time.time', return_value=1700000000):
            self.cache.reply(self.rpc, {'interface_name': 'et-*'}, self.fetch)
        self.now.return_value = 1060
        collector = StatusCollector(SimpleNamespace(optics_cache=self.cache))
        values = [s for family in collector.optics_freshness() for s in family.samples]
        self.assertEqual(values[0].value, 60)
        self.assertEqual(values[1].value, 1700000000)
        self.now.return_value = 1300
        self.assertEqual([s for f in collector.optics_freshness() for s in f.samples], [])


if __name__ == '__main__':
    unittest.main()
