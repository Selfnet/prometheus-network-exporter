from prometheus_junos_exporter.config.definitions.junos import wrapping

FUNCTIONS = {
    'is_ok': wrapping.is_ok,
    'floatify': wrapping.floatify,
    'fan_power_temp_status': wrapping.fan_power_temp_status,
    'temp_celsius': wrapping.temp_celsius,
    'reboot': wrapping.reboot,
    'cpu_idle': wrapping.cpu_idle,
    'cpu_usage': wrapping.cpu_usage,
    'ram': wrapping.ram,
    'ram_usage': wrapping.ram_usage
}

METRICS = {
    'Counter': 'counter',
    'Gauge': 'gauge'
}

def create_metrik(metrik_name, registry, key, labels, metriken, function=None):
    if metriken.get(key) is not None:
        try:
            if function:
                registry.add_metric(metrik_name, FUNCTIONS[function](
                    metriken.get(key)), labels=labels)
            else:
                registry.add_metric(
                    metrik_name, metriken.get(key), labels=labels)
        except (ValueError, KeyError) as e:
            print("Error :: {}".format(e))