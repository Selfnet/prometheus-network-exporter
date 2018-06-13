#!/usr/bin/env python3.5

'''
    Create a custom pyez driver for
    performance.
'''

import socket
from jnpr.junos import Device
from jnpr.junos.exception import RpcError
from prometheus_junos_exporter.views.optic import PhyPortDiagTable
from prometheus_junos_exporter.views.interface_metrics import MetricsTable
from prometheus_junos_exporter.views.bgp import BGPNeighborTable
from prometheus_junos_exporter.views.environment import RoutingEngineTable, EnvironmentTable


def get_specific_ports_information(dev, interface_junos_notations):
    result = {}
    for interface_name in interface_junos_notations:
        ports = dict(MetricsTable(dev).get(interface_name=interface_name))
        intopticdiag = dict(PhyPortDiagTable(
            dev).get(interface_name=interface_name))
        for port in ports.keys():
            result[port] = {**ports[port], **intopticdiag.get(port, {})}
    return result


def get_all_ports_information(dev):
    result = {}
    ports = dict(MetricsTable(dev).get())
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
        **{'Temp': {k: dict(v) for k, v in temperatures.items() if 'Temp' ==  dict(v)['class']}},
        **{'Fans': {k: dict(v) for k, v in temperatures.items() if 'Fans' == dict(v)['class']}},
        **{'Power': {k: dict(v) for k, v in temperatures.items() if 'Power' == dict(v)['class']}}
    }


def lookup(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror):
        return ip


def get_bgp_information(dev):
    try:
        bgp = dict(BGPNeighborTable(dev).get())
    except RpcError:
        return {}
    return {lookup(k): dict(v) for k, v in bgp.items()}
