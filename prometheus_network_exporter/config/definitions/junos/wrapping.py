
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


