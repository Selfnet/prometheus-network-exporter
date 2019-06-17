
import os
import yaml
# If u want to have more metrics. You must edit the config/metrics_definitions.yml
file_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'metrics_definition.yml')
with open(file_dir, 'r') as metrics_definitions:
    DEFINITIONS = yaml.safe_load(metrics_definitions).get('DEFINITIONS', {})

# Get the Metrics DEFINITIONS
METRICS_BASE = DEFINITIONS.get('METRICS_BASE', {})
NETWORK_REGEXES = DEFINITIONS.get('NETWORK_REGEXES', [])
OSPF_METRICS = DEFINITIONS.get('OSPF_METRICS', {})
NETWORK_METRICS = DEFINITIONS.get('NETWORK_METRICS', {})
ENVIRONMENT_METRICS = DEFINITIONS.get('ENVIRONMENT_METRICS', {})
OSPF_LABEL_WRAPPER = DEFINITIONS.get('OSPF_LABEL_WRAPPER', [])
NETWORK_LABEL_WRAPPER = DEFINITIONS.get('NETWORK_LABEL_WRAPPER', [])
ENVIRONMENT_LABEL_WRAPPER = DEFINITIONS.get('ENVIRONMENT_LABEL_WRAPPER', [])
BGP_METRICS = DEFINITIONS.get('BGP_METRICS', {})
BGP_LABEL_WRAPPER = DEFINITIONS.get('BGP_LABEL_WRAPPER', [])
IGMP_NETWORKS = DEFINITIONS.get('IGMP_NETWORKS', {})


def is_ok(boolean):
    if isinstance(boolean, bool):
        if boolean:
            return 1
        return 0
    elif isinstance(boolean, str):
        if boolean.lower() in ['up', 'ok', 'established']:
            return 1
        return 0
    else:
        raise Exception("Unknown Type")

# this function is for the api


def boolify(string):
    return 'true' in string.lower()


def floatify(string):
    if "- Inf" in string:
        return - float('inf')
    elif "Inf" in string:
        return float('inf')
    return float(string)


def fan_power_temp_status(metric, registry, labels, data, create_metric=None):
    for sensorname, information in data.items():
        labels['sensorname'] = sensorname
        create_metric(metric, registry, 'status', labels,
                      information, function='is_ok')


def temp_celsius(metric, registry, labels, data, create_metric=None):
    for sensorname, information in data.items():
        labels['sensorname'] = sensorname
        create_metric(metric, registry, 'temperature',
                      labels, information)


def reboot(metric, registry, labels, data, create_metric=None):
    reason_string = data.get('last_reboot_reason', '')
    reason = 1
    for a in ["failure", "error", "failed"]:
        if a in reason_string.lower():
            reason = 0
    labels['reboot_reason'] = reason_string
    registry.add_metric(metric, reason, labels=labels)


def cpu_usage(metric, registry, labels, data, create_metric=None):
    for slot, perf in data.items():
        label = "cpu_{}".format(str(slot))
        labels['cpu'] = label
        cpu_usage = 100 - int(perf['cpu-idle'])
        registry.add_metric(metric, cpu_usage, labels=labels)


def cpu_idle(metric, registry, labels, data, create_metric=None):
    for slot, perf in data.items():
        label = "cpu_{}".format(str(slot))
        labels['cpu'] = label
        cpu_idle = int(perf['cpu-idle'])
        registry.add_metric(metric, cpu_idle, labels=labels)


def ram_usage(metric, registry, labels, data, create_metric=None):
    for slot, perf in data.items():
        label = "ram_{}".format(str(slot))
        labels['ram'] = label
        memory_complete = perf['memory-dram-size'].lower().replace("mb",
                                                                   "").strip()
        memory_complete = int(memory_complete)
        memory_usage = int(perf['memory-buffer-utilization'])
        memory_bytes_usage = (memory_complete * memory_usage / 100) * 1049000
        registry.add_metric(metric, memory_bytes_usage, labels=labels)


def ram(metric, registry, labels, data, create_metric=None):
    for slot, perf in data.items():
        label = "ram_{}".format(str(slot))
        labels['ram'] = label
        memory_complete = perf['memory-dram-size'].lower().replace("mb",
                                                                   "").strip()
        memory_complete = int(memory_complete)
        memory_bytes = memory_complete * 1049000
        registry.add_metric(metric, memory_bytes, labels=labels)


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
