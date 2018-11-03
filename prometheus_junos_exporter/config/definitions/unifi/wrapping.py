import sys
import os
import time
import datetime
from getpass import getpass, getuser
import yaml


with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'metrics_definition.yml'), 'r') as metrics_definitions:
    DEFINITIONS = yaml.load(metrics_definitions).get('DEFINITIONS', {})

METRICS_BASE = DEFINITIONS.get('METRICS_BASE', {})
NETWORK_METRICS = DEFINITIONS.get('NETWORK_METRICS', {})
NETWORK_LABEL_WRAPPER = DEFINITIONS.get('NETWORK_LABEL_WRAPPER', {})
