import unittest
from unittest.mock import Mock

from prometheus_network_exporter.devices.junosdevice import EnvironmentCollector


class EnvironmentStateTests(unittest.TestCase):
    def collector(self, environment):
        device = Mock()
        device.get_environment.return_value = environment
        collector = EnvironmentCollector(device)
        collector.prometheus_metrics = {
            key: metric
            for key, metric in collector.prometheus_metrics.items()
            if metric.json_key in ("Power", "Fans", "Temp")
        }
        return collector

    def collect(self, collector):
        return [sample for metric in collector.collect() for sample in metric.samples]

    def test_states_preserved_without_changing_legacy_metrics(self):
        collector = self.collector(
            {
                "Power": {
                    "Power Supply 0": {"status": "OK"},
                    "Power Supply 1": {"status": "Absent"},
                    "Power Supply 2": {"status": "Failed"},
                },
                "Fans": {"Fan 0": {"status": "OK"}},
                "Temp": {"Board": {"status": "Testing", "temperature": 35}},
            }
        )
        samples = self.collect(collector)
        states = [s for s in samples if s.name == "pyez_junos_device_environment_info"]
        self.assertEqual(len(states), 5)
        self.assertEqual({s.labels["status"] for s in states}, {"OK", "Absent", "Failed", "Testing"})
        self.assertEqual({s.labels["component_class"] for s in states}, {"Power", "Fans", "Temp"})
        self.assertTrue(all(s.value == 1 for s in states))
        power = {s.labels["sensorname"]: s.value for s in samples if s.name == "pyez_junos_device_power_status"}
        self.assertEqual(power, {"Power Supply 0": 1, "Power Supply 1": 0, "Power Supply 2": 0})
        collector.device.get_environment.assert_called_once_with()

    def test_missing_status_is_unknown_and_missing_component_is_absent_from_metrics(self):
        collector = self.collector({})
        metric = collector.environment_states(
            {"Power": {"PSU0": {}, "PSU1": {"status": None}, "PSU2": {"status": "  "}}}
        )
        self.assertEqual(len(metric.samples), 3)
        self.assertTrue(all(s.labels["status"] == "unknown" for s in metric.samples))
        self.assertEqual(collector.environment_states({}).samples, [])

    def test_state_changes_do_not_leave_previous_samples(self):
        data = {"Power": {"PSU0": {"status": "Absent"}}, "Fans": {}, "Temp": {}}
        collector = self.collector(data)
        self.collect(collector)
        data["Power"]["PSU0"]["status"] = "OK"
        states = [s for s in self.collect(collector) if s.name == "pyez_junos_device_environment_info"]
        self.assertEqual(len(states), 1)
        self.assertEqual(states[0].labels["status"], "OK")


if __name__ == "__main__":
    unittest.main()
