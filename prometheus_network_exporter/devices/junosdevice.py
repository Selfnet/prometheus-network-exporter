
'''
    General Device 
'''
from jnpr.junos import Device
from jnpr.junos.exception import RpcError, ConnectError, ConnectClosedError, RpcTimeoutError, FactLoopError
import ipaddress
from prometheus_network_exporter.devices import basedevice
from prometheus_network_exporter.config.definitions.junos import wrapping
from prometheus_network_exporter.utitlities import create_metric_params, create_metric, FUNCTIONS, METRICS

from prometheus_network_exporter.views.junos.optic import PhyPortDiagTable
from prometheus_network_exporter.views.junos.interface_metrics import MetricsTable
from prometheus_network_exporter.views.junos.bgp import BGPNeighborTable
from prometheus_network_exporter.views.junos.environment import RoutingEngineTable, EnvironmentTable
from prometheus_network_exporter.views.junos.ospf import OspfNeighborTable, Ospf3NeighborTable
from prometheus_network_exporter.views.junos.igmp import IGMPGroupTable


class JuniperNetworkDevice(basedevice.Device):
    def __init__(self, hostname, user=None, password=None, port=22, ssh_private_key_file=None, ssh_config=None):
        device = Device(host=hostname,
                        user=user,
                        ssh_private_key_file=ssh_private_key_file,
                        ssh_config=ssh_config,
                        password=password,
                        port=port,
                        gather_facts=False)
        super().__init__(hostname, device)

    def get_bgp(self):
        try:
            bgp = dict(BGPNeighborTable(self.device).get())
        except RpcError:
            return {}
        bgp = {k: dict(v) for k, v in bgp.items()}
        for information in bgp.values():
            information['peername'] = self.lookup(information['peeraddr'])
        return bgp

    def get_interface(self, interface_names=None, ospf=False, optics=False):
        result = {}
        if not interface_names:
            ports = dict(MetricsTable(self.device).get())
            if optics:
                intopticdiag = self.get_optics()
            else:
                intopticdiag = {}
            if ospf:
                ospf = self.get_ospf()
            else:
                ospf = {}
            for port in ports.keys():
                result[port] = {**ports[port], **
                                intopticdiag.get(port, {}), **ospf.get(port, {})}
        else:
            for interface_name in interface_names:
                ports = dict(MetricsTable(self.device).get(
                    interface_name=interface_name))
                if optics:
                    intopticdiag = self.get_optics(
                        interface_name=interface_name)
                else:
                    intopticdiag = {}
                if ospf:
                    ospf = self.get_ospf(interface_name=interface_name)
                else:
                    ospf = {}
                for port in ports.keys():
                    result[port] = {**ports[port], **
                                    intopticdiag.get(port, {}), **ospf.get(port, {})}
        return result

    def get_environment(self):
        facts = self.device.facts
        uptime = self.device.uptime
        rengine = RoutingEngineTable(self.device).get()
        temperatures = EnvironmentTable(self.device).get()
        return {
            **facts,
            **{'uptime': uptime},
            **{'re_loads': {k: dict(v) for k, v in rengine.items()}},
            **{'Temp': {k: dict(v) for k, v in temperatures.items() if 'Temp' == dict(v)['class']}},
            **{'Fans': {k: dict(v) for k, v in temperatures.items() if 'Fans' == dict(v)['class']}},
            **{'Power': {k: dict(v) for k, v in temperatures.items() if 'Power' == dict(v)['class']}}
        }

    def get_igmp(self):
        igmp = dict(IGMPGroupTable(self.device).get())
        igmp = {k: dict(v) for k, v in igmp.items() if not 'local' in k}
        for v in igmp.values():
            if isinstance(v['mgm_addresses'], str):
                v['mgm_addresses'] = [v['mgm_addresses']]
        return igmp

    def lookup_ospf(self, ospf):
        if 'neighbor_id' in ospf.keys():
            ospf['neighbor_id'] = self.lookup(ospf['neighbor_id'])
        return ospf

    def get_ospf(self, interface_name=None):
        result = {}
        ospf = dict(OspfNeighborTable(self.device).get()) if interface_name is None else dict(
            OspfNeighborTable(self.device).get(interface=interface_name))
        ospf3 = dict(Ospf3NeighborTable(self.device).get()) if interface_name is None else dict(
            Ospf3NeighborTable(self.device).get(interface=interface_name))
        for interface_name in ospf.keys():
            splitted_name = interface_name.split('.')
            interface = splitted_name[0]
            try:
                unit = int(splitted_name[1])
                if interface not in result.keys():
                    result[interface] = {}
                result[interface]['ospf'] = {unit: self.lookup_ospf(
                    dict(ospf.get(interface_name, {})))}
                result[interface]['ospf3'] = {unit: self.lookup_ospf(
                    dict(ospf3.get(interface_name, {})))}
            except IndexError as e:
                print(e)

        return result

    def get_optics(self, interface_name=None):
        return dict(PhyPortDiagTable(self.device).get()) if interface_name is None else dict(
            PhyPortDiagTable(self.device).get(interface_name=interface_name))

    def is_connected(self):
        return self.device.connected

    def connect(self):
        if self.is_connected():
            return True
        try:
            self.device.open()
            return True
        except ConnectError as err:
            print(err)
        return False

    def disconnect(self):
        if self.is_connected():
            self.device.close()
        return self.is_connected()


class JuniperMetrics(basedevice.Metrics):
    def __init__(self, *args, **kwargs):
        super(JuniperMetrics, self).__init__(*args, **kwargs)

    def get_igmp_metrics(self, registry, dev, hostname):
        igmp_groups = dev.get_igmp()
        ignored_networks = [ipaddress.ip_network(
            net) for net in wrapping.IGMP_NETWORKS.get('ignore', {}).keys()]
        networks = [ipaddress.ip_network(
            prefix) for prefix in wrapping.IGMP_NETWORKS.get('allow', {}).keys()]
        counter = {}
        metric_name = "{}_{}_{}".format(wrapping.METRICS_BASE.get(
            'base', 'junos'),
            wrapping.METRICS_BASE.get('igmp', 'igmp'),
            'broadcasts_total')
        description = "Users subscribed on broadcasting company/channel"
        for firm in wrapping.IGMP_NETWORKS['allow'].values():
            counter[firm] = 0
        registry.register(metric_name, description, 'gauge')
        for network in networks:
            for mgm_addresses in igmp_groups.values():
                for address in mgm_addresses['mgm_addresses']:
                    current_addr = ipaddress.ip_address(address)
                    if current_addr in network:
                        for ignore in ignored_networks:
                            if current_addr not in ignore:
                                counter[wrapping.IGMP_NETWORKS['allow']
                                        [str(network)]] += 1

            create_metric(metric_name, registry, wrapping.IGMP_NETWORKS['allow'][str(network)], {
                          'broadcaster': wrapping.IGMP_NETWORKS['allow'][str(network)]}, counter)

    def get_interface_metrics(self, registry, dev, hostname, access=True, ospf=True, optics=True):
        """
        Get interface metrics
        """
        # interfaces
        interfaces = {}
        if access:
            interfaces = dev.get_interface(
                interface_names=wrapping.NETWORK_REGEXES, optics=optics, ospf=ospf)
        else:
            interfaces = dev.get_interface(optics=optics, ospf=ospf)
        if ospf:
            for MetricName, MetricFamily in METRICS.items():
                for metric_def in wrapping.OSPF_METRICS.get(MetricName, []):
                    name, description, key, function, _ = create_metric_params(
                        metric_def)
                    for ospf in ['ospf', 'ospf3']:
                        metric_name = "{}_{}_{}_{}".format(wrapping.METRICS_BASE.get(
                            'base', 'junos'),
                            wrapping.METRICS_BASE.get(
                                'interface', 'interface'),
                            ospf,
                            name)
                        registry.register(
                            metric_name, description, MetricFamily)
                        for interface, metrics in interfaces.items():
                            for unit, data in metrics.get(ospf, {}).items():
                                if data.get(key) is not None:
                                    labels_data = {'interface': interface,
                                                   'unit': unit}
                                    labels_variable = {label['label']: metrics.get(
                                        label['key'], "") for label in wrapping.NETWORK_LABEL_WRAPPER}
                                    labels_ospf = {label['label']: data.get(
                                        label['key'], "") for label in wrapping.OSPF_LABEL_WRAPPER}
                                    labels = {**labels_data, **
                                              labels_variable, **labels_ospf}
                                    create_metric(metric_name,
                                                  registry, key, labels, data, function=function)

        for MetricName, MetricFamily in METRICS.items():
            for metric_def in wrapping.NETWORK_METRICS.get(MetricName, []):
                metric_name, description, key, function, _ = create_metric_params(
                    metric_def)
                metric_name = "{}_{}_{}".format(wrapping.METRICS_BASE.get(
                    'base', 'junos'), wrapping.METRICS_BASE.get('interface', 'interface'), metric_name)
                registry.register(metric_name, description, MetricFamily)
                for interface, metrics in interfaces.items():
                    if metrics.get(key) is not None:
                        labels_data = {'interface': interface}
                        labels_variable = {label['label']: metrics.get(
                            label['key'], "") for label in wrapping.NETWORK_LABEL_WRAPPER}
                        labels = {**labels_data, **labels_variable}
                        create_metric(metric_name,
                                      registry, key, labels, metrics, function=function)

    def get_environment_metrics(self, registry, dev, hostname):
        """
        Get environment metrics
        """
        environment = dev.get_environment()
        for MetricName, MetricFamily in METRICS.items():
            for metric_def in wrapping.ENVIRONMENT_METRICS.get(MetricName, []):
                metric_name, description, key, function, specific = create_metric_params(
                    metric_def)
                metric_name = "{}_{}_{}".format(
                    wrapping.METRICS_BASE['base'], wrapping.METRICS_BASE['device'], metric_name)
                registry.register(metric_name, description, MetricFamily)
                labels_data = {}
                labels_variable = {label['label']: environment.get(
                    label['key'], "") for label in wrapping.ENVIRONMENT_LABEL_WRAPPER}
                labels = {**labels_data, **labels_variable}
                if specific and function:
                    data = environment.get(key, None)
                    FUNCTIONS[function](
                        metric_name, registry, labels, data, create_metric=create_metric)
                elif environment.get(key):
                    create_metric(
                        metric_name, registry, key, labels, environment, function=function)

    def get_bgp_metrics(self, registry, dev, hostname):
        """
        Get BGP neighbor metrics
        """
        bgp = dev.get_bgp()
        for MetricName, MetricFamily in METRICS.items():
            for metric_def in wrapping.BGP_METRICS.get(MetricName, []):
                metric_name, description, key, function, _ = create_metric_params(
                    metric_def)
                metric_name = "{}_{}_{}".format(
                    wrapping.METRICS_BASE['base'], wrapping.METRICS_BASE['bgp'], metric_name)
                registry.register(metric_name, description, MetricFamily)
                if bgp:
                    for peeraddr, metrics in bgp.items():
                        if metrics.get(key) is not None:
                            labels_data = {'peeraddr': peeraddr}
                            labels_variable = {label['key']: metrics.get(
                                label['key'], "") for label in wrapping.BGP_LABEL_WRAPPER}
                            labels = {**labels_data, **labels_variable}
                            create_metric(
                                metric_name, registry, key, labels, metrics, function=function)

    def metrics(self, types, dev, registry):
        optics = ospf = True
        success = dev.connect()
        if not success:
            self.exception_counter.labels(
                exception='ConnectError', collector='JuniperMetrics', hostname=dev.hostname).inc()
            return 500, "Connection Error", "Cannot connect to device {}.".format(dev.hostname)
        try:
            dev.device.timeout = 50
            if not 'ospf' in types:
                ospf = False
            if not 'optics' in types:
                optics = False
            if 'interface' in types:
                self.get_interface_metrics(registry, dev, dev.hostname,
                                           access=False, optics=optics, ospf=ospf)
            if 'interface_specifics' in types:
                self.get_interface_metrics(registry, dev, dev.hostname,
                                           access=True, optics=optics, ospf=ospf)
            if 'environment' in types:
                self.get_environment_metrics(registry, dev, dev.hostname)
            if 'bgp' in types:
                self.get_bgp_metrics(registry, dev, dev.hostname)
            if 'igmp' in types:
                self.get_igmp_metrics(registry, dev, dev.hostname)
            dev.disconnect()
        except AttributeError as e:
            print(e)
            dev.disconnect()
            self.exception_counter.labels(
                exception='AttributeError', collector='JuniperMetrics', hostname=dev.hostname).inc()
            hostname = dev.hostname
            del(dev)
            return 500, "Device unreachable", "Device {} unreachable".format(hostname)
        except ConnectClosedError as e:
            print(e)
            dev.disconnect()
            self.exception_counter.labels(
                exception='ConnectClosedError', collector='JuniperMetrics', hostname=dev.hostname).inc()
            return 500, "Connection closed unexpectedly!", "Device {} unreachable".format(dev.hostname)
        except RpcTimeoutError as e:
            print(e)
            dev.disconnect()
            self.exception_counter.labels(
                exception='RpcTimeoutError', collector='JuniperMetrics', hostname=dev.hostname).inc()
            return 500, "RPC command timed out!", "Device {} unreachable".format(dev.hostname)
        except FactLoopError as e:
            print(e)
            dev.disconnect()
            self.exception_counter.labels(
                exception='FactLoopError', collector='JuniperMetrics', hostname=dev.hostname).inc()
            return 500, "FactLoopError!", "Device {} unreachable".format(dev.hostname)
        return 200, "OK", registry.collect()
