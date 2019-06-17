import collections
from prometheus_network_exporter.config.definitions.junos import wrapping as junos


FUNCTIONS = {
    'is_ok': junos.is_ok,
    'floatify': junos.floatify,
    'fan_power_temp_status': junos.fan_power_temp_status,
    'temp_celsius': junos.temp_celsius,
    'reboot': junos.reboot,
    'cpu_idle': junos.cpu_idle,
    'cpu_usage': junos.cpu_usage,
    'ram': junos.ram,
    'ram_usage': junos.ram_usage
}

METRICS = {
    'Counter': 'counter',
    'Gauge': 'gauge'
}


def create_metric_params(metric_def, call='interfaces'):
    metric_name = metric_def['metric']
    key = metric_def['key']
    description = metric_def.get('description', '')
    type_of = metric_def.get('type', None)
    function = metric_def.get('function', None)
    specific = metric_def.get('specific', False)
    if type_of:
        metric_name = '{}_{}'.format(metric_name, type_of)
    return metric_name, description, key, function, specific


def create_metric(metric_name, registry, key, labels, metrics, function=None):
    if metrics.get(key) is not None:
        try:
            if function:
                registry.add_metric(metric_name, FUNCTIONS[function](
                    metrics.get(key)), labels=labels)
            else:
                registry.add_metric(
                    metric_name, metrics.get(key), labels=labels)
        except (ValueError, KeyError) as e:
            print("Error :: {}".format(e))


def flatten(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
