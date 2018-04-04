#!/usr/bin/env python3.5

'''
    Create a custom pyez driver for
    performance.
'''

from jnpr.junos import Device
from jnpr.junos.op.intopticdiag import PhyPortDiagTable
from views.interface_metriks import MetriksTable
from views.environment import RoutingEngineTable, EnvironmentTable
from pprint import pprint


def get_specific_ports_information(dev, interface_junos_notations):
    result = {}
    for interface_name in interface_junos_notations:
        ports = dict(MetriksTable(dev).get(interface_name=interface_name))
        intopticdiag = dict(PhyPortDiagTable(
            dev).get(interface_name=interface_name))
        for port in ports.keys():
            result[port] = {**ports[port], **intopticdiag.get(port, {})}
    return result


def get_all_ports_information(dev):
    result = {}
    ports = dict(MetriksTable(dev).get())
    intopticdiag = dict(PhyPortDiagTable(dev).get())
    for port in ports.keys():
        result[port] = {**ports[port], **intopticdiag.get(port, {})}
    return result


def get_environment(dev):
    facts = dev.facts
    uptime = dev.uptime
    rengine = RoutingEngineTable(dev).get()
    temperatures = EnvironmentTable(dev).get()

    return {
        **facts,
        **{'uptime': uptime},
        **{'re_loads': {k: dict(v) for k, v in rengine.items()}},
        **{'Temp': {k: dict(v) for k, v in temperatures.items() if 'Temp' in dict(v)['class']}},
        **{'Fans': {k: dict(v) for k, v in temperatures.items() if 'Fans' in dict(v)['class']}},
        **{'Power': {k: dict(v) for k, v in temperatures.items() if 'Power' in dict(v)['class']}}
    }
