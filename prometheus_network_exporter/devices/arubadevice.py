import json

from prometheus_network_exporter.devices import basedevice

from arubaos_client.client import MobilityControllerAPIClient

BASE = "arubaos"

STATS_JSON = """
{
    "name": {
        "stats": {
            "BSSID": {
                "5g": {
                    "channel": 0.0,
                    "channel_frame_retry_rate": 0.0,
                    "channel_frame_low_speed_rate": 0.0,
                    "channel_frame_non_unicast_rate": 0.0,
                    "channel_frame_fragmentation_rate": 0.0,
                    "channel_frame_error_rate": 0.0,
                    "channel_bandwidth_rate_kbps": 0.0,
                    "channel_noise": 0.0,
                    "bssid": "",
                    "bss_frame_retry_rate": 0.0,
                    "bss_frame_low_speed_rate": 0.0,
                    "bss_frame_non_unicast_rate": 0.0,
                    "bss_frame_fragmentation_rate": 0.0,
                    "bss_frame_receive_error_rate": 0.0,
                    "bss_bandwidth_rate_kbps": 0.0,
                    "bss_tx_packets": 0.0,
                    "bss_rx_packets": 0.0,
                    "bss_tx_bytes": 0.0,
                    "bss_rx_bytes": 0.0,
                    "bss_snr": 0.0,
                    "bss_tx_rate": 0.0,
                    "bss_rx_rate": 0.0
                },
                "2g": {
                    "channel": 0.0,
                    "channel_frame_retry_rate": 0.0,
                    "channel_frame_low_speed_rate": 0.0,
                    "channel_frame_non_unicast_rate": 0.0,
                    "channel_frame_fragmentation_rate": 0.0,
                    "channel_frame_error_rate": 0.0,
                    "channel_bandwidth_rate_kbps": 0.0,
                    "channel_noise": 0.0,
                    "bssid": "",
                    "bss_frame_retry_rate": 0.0,
                    "bss_frame_low_speed_rate": 0.0,
                    "bss_frame_non_unicast_rate": 0.0,
                    "bss_frame_fragmentation_rate": 0.0,
                    "bss_frame_receive_error_rate": 0.0,
                    "bss_bandwidth_rate_kbps": 0.0,
                    "bss_tx_packets": 0.0,
                    "bss_rx_packets": 0.0,
                    "bss_tx_bytes": 0.0,
                    "bss_rx_bytes": 0.0,
                    "bss_snr": 0.0,
                    "bss_tx_rate": 0.0,
                    "bss_rx_rate": 0.0
                }
            }
        },
        "Active AP Table": [
            {
                "11a Clients": "",
                "11g Clients": "",
                "AP Type": "",
                "Flags": "",
                "Group": "",
                "IP Address": "",
                "Name": "",
                "Outer IP": "",
                "Uptime": 0,
                "11a_clients": 0.0,
                "11g_clients": 0.0,
                "11a_info": {
                    "eirp": 0.0,
                    "max_eirp": 0.0
                },
                "11g_info": {
                    "eirp": 0.0,
                    "max_eirp": 0.0
                }
            }
        ],
        "_data": {
            "flags": {
                "1": "802.1x authenticated AP",
                "2": "Using IKE version 2",
                "A": "Enet1 in active/standby mode",
                "B": "Battery Boost On",
                "C": "Cellular",
                "D": "Disconn. Extra Calls On",
                "E": "Wired AP enabled",
                "F": "AP failed 802.1x authentication",
                "H": "Hotspot Enabled",
                "K": "802.11K Enabled",
                "L": "Client Balancing Enabled",
                "M": "Mesh",
                "N": "802.11b protection disabled",
                "P": "PPPOE",
                "R": "Remote AP",
                "S": "AP connected as standby",
                "X": "Maintenance Mode",
                "a": "Reduce ARP packets in the air",
                "d": "Drop Mcast/Bcast On",
                "u": "Custom-Cert RAP",
                "i": "Provisioned as Indoor",
                "o": "Provisioned as Outdoor",
                "r": "802.11r Enabled",
                "f": "No Spectrum FFT support",
                "Q": "DFS CAC timer running",
                "T": "Flex Radio Mode is 2.4GHz+5GHz",
                "U": "Flex Radio Mode is 5GHz",
                "V": "Flex Radio Mode is 2.4GHz",
                "e": "custom EST certChannel"
            }
        }
    }
}
"""


class ArubaNetworkDevice(basedevice.Device):
    def __init__(self, hostname, username=None, password=None, port=4343, proxy=None, verify=False, protocol='https'):
        device = MobilityControllerAPIClient(
            username=username, password=password, url='{protocol}://{hostname}:{port}'.format(
                protocol=protocol, hostname=hostname, port=port), proxy=proxy, verify=verify)
        super().__init__(hostname, device)

    def connect(self):
        try:
            self.device.login()
            return True
        except:
            return False

    def disconnect(self):
        self.device.logout()
        return True

    def is_connected(self):
        try:
            self.device.get_clients()
        except:
            return False
        return True


class ArubaMetrics(basedevice.Metrics):
    def __init__(self, *args, **kwargs):
        super(ArubaMetrics, self).__init__(*args, **kwargs)

    def get_system_information(self, registry, dev, hostname):
        data = dev.device.sys_info()
        metric_key = 'device'
        metric_software_version = "{}_{}_software_version".format(
            BASE, metric_key)
        metric_hardware_model = "{}_{}_hardware_model".format(BASE, metric_key)

        sw_description = "Version of the installed software."
        hw_description = "Hardware model number of the scraped device."

        registry.register(metric_software_version, sw_description, 'gauge')
        registry.register(metric_hardware_model, hw_description, 'gauge')

        software_version = data.get('_local', {}).get('_sw_version')
        hardware_model = data.get('_global', {}).get('_model')

        registry.add_metric(metric_software_version, 1.0 if software_version else 0.0, labels={
                            "software_version": software_version})
        registry.add_metric(metric_hardware_model, 1.0 if hardware_model else 0.0, labels={
                            'model': hardware_model})

    def get_clients(self, registry, dev, hostname):
        key = '_data'
        metric_key = 'clients'
        clients_2g = dev.device.clients_2g()[key]
        clients_5g = dev.device.clients_5g()[key]

        metric_clients_total_2g = "{}_{}_{}_{}".format(
            BASE, metric_key, '2g', 'actual')
        metric_clients_total_5g = "{}_{}_{}_{}".format(
            BASE, metric_key, '5g', 'actual')
        metric_clients_max_2g = "{}_{}_{}_{}".format(
            BASE, metric_key, '2g', 'max')
        metric_clients_max_5g = "{}_{}_{}_{}".format(
            BASE, metric_key, '5g', 'max')

        description = "Total clients connected to Access Controller"
        max_description = "Max clients connected to Access Controller"

        registry.register(metric_clients_total_2g, description, 'gauge')
        registry.register(metric_clients_total_5g, description, 'gauge')
        registry.register(metric_clients_max_2g, max_description, 'gauge')
        registry.register(metric_clients_max_5g, max_description, 'gauge')

        registry.add_metric(metric_clients_total_2g,
                            clients_2g['User Entries']['actual'])
        registry.add_metric(metric_clients_total_5g,
                            clients_5g['User Entries']['actual'])
        registry.add_metric(metric_clients_max_2g,
                            clients_2g['User Entries']['max'])
        registry.add_metric(metric_clients_max_5g,
                            clients_5g['User Entries']['max'])

    def get_cpu(self, registry, dev, hostname):
        data = dev.device.cpu_load()
        key = 'cpu'
        for stat in data[key].keys():
            name = "{}_{}_{}_ratio".format(BASE, key, stat)
            description = "Metric in percentage (0-100%)."
            type = 'gauge'
            registry.register(name, description, type)
        for stat, value in data[key].items():
            name = "{}_{}_{}_ratio".format(BASE, key, stat)
            registry.add_metric(name, value)

    def get_memory(self, registry, dev, hostname):
        data = dev.device.memory_usage()
        key = 'ram'
        for stat in data[key].keys():
            name = "{}_{}_{}_bytes".format(BASE, key, stat)
            description = "Metric in bytes."
            type = 'gauge'
            registry.register(name, description, type)
        for stat, value in data.get(key, {}).items():
            name = "{}_{}_{}_bytes".format(BASE, key, stat)
            registry.add_metric(name, value)

    def get_access_point_state(self, registry, dev, hostname):
        metric_key = 'ap'
        aps = dev.device.aps()
        metric_status = "{}_{}_status".format(BASE, metric_key)
        metric_uptime = "{}_{}_status_seconds".format(BASE, metric_key)
        description_status = "Status of an AP((0, DOWN) (1, UP))"
        description_uptime = "Duration of AP status in seconds."
        registry.register(metric_status, description_status, 'gauge')
        registry.register(metric_uptime, description_uptime, 'gauge')
        for ap in aps.get('AP Database', []):
            name = ap['Name']
            group = ap['Group']
            status = ap['Status']
            registry.add_metric(metric_status, 1.0 if status['status'] else 0.0, labels={
                                'name': name, 'group': group})
            registry.add_metric(metric_uptime, status['uptime'], labels={
                                'name': name, 'group': group})

    def get_access_point_statistics(self, registry, dev, hostname):
        metric_key = 'ap'

        aps = dev.device.aps()
        ap_names = [ap.get('Name') for ap in aps.get('AP Database', [])]
        ap_stats = []
        for ap_name in ap_names:
            ap_stats.append(dev.device.ap(ap_name=ap_name))

        metrics = json.loads(STATS_JSON)

        for _, data in metrics.items():
            for bssid in data.get('stats', {}).keys():
                for frequency in data.get('stats', {}).get(bssid, {}).keys():
                    for key in data.get('stats', {}).get(bssid, {}).get(frequency, {}).keys():
                        if key in ['bss_tx_packets', 'bss_rx_packets', 'bss_tx_bytes', 'bss_rx_bytes']:
                            end = 'total'
                            metric_type = 'counter'
                        else:
                            end = None
                            metric_type = 'gauge'
                        if key != 'bssid':
                            metric_name = "{}_{}_{}".format(
                                BASE, metric_key, key)
                            if end:
                                metric_name = "{}_{}".format(metric_name, end)
                            registry.register(
                                metric_name,
                                'ap stats',
                                metric_type)
                    break
                break
            try:
                for key in data.get('Active AP Table', [{}])[0].keys():
                    if key in ["Uptime"]:
                        registry.register("{}_{}_uptime_seconds".format(BASE, metric_key),
                                          "AP Uptime in seconds",
                                          'gauge')

                    elif key in ["11a_info", "11g_info"]:
                        for eirp in data.get('Active AP Table', [{}])[0][key].keys():
                            registry.register("{}_{}_{}_{}".format(
                                BASE, metric_key, key, eirp), "EIRP Information of AP", 'gauge')
            except IndexError:
                pass

        for ap_stat in ap_stats:
            for ap_name, data in ap_stat.items():
                for bssid in data.get('stats', {}).keys():
                    for frequency in data.get('stats', {}).get(bssid, {}).keys():
                        for key in data.get('stats', {}).get(bssid, {}).get(frequency, {}).keys():
                            if key in ['bss_tx_packets', 'bss_rx_packets', 'bss_tx_bytes', 'bss_rx_bytes']:
                                end = 'total'
                            else:
                                end = None
                            if key != 'bssid':
                                try:
                                    group = data["Active AP Table"][0]['Group']
                                except IndexError:
                                    group = 'Unknown'
                                metric_name = "{}_{}_{}".format(
                                    BASE, metric_key, key)
                                if end:
                                    metric_name = "{}_{}".format(
                                        metric_name, end)
                                registry.add_metric(
                                    metric_name,
                                    data.get('stats', {}).get(bssid, {}).get(
                                        frequency, {}).get(key, None),
                                    labels={
                                        'name': ap_name,
                                        'bssid': bssid,
                                        'band': frequency,
                                        'group': group
                                    }
                                )
                try:
                    for key in data.get('Active AP Table', [{}])[0].keys():
                        try:
                            group = data["Active AP Table"][0]['Group']
                        except IndexError:
                            group = 'Unknown'
                        if key in ["Uptime"]:
                            registry.add_metric("{}_{}_uptime_seconds".format(BASE, metric_key), data['Active AP Table'][0]['Uptime'], labels={
                                                'name': ap_name, 'group': group})
                        elif key in ["11a_info", "11g_info"]:
                            for eirp in data.get('Active AP Table', [{}])[0].get(key, {}).keys():
                                registry.add_metric(
                                    "{}_{}_{}_{}".format(
                                        BASE, metric_key, key, eirp),
                                    data.get('Active AP Table', [{}])[0].get(key, {}).get(eirp),
                                    labels={
                                        'name': ap_name,
                                        'group': group
                                    }
                                )
                except IndexError:
                    pass

    def metrics(self, types, dev, registry):
        dev.connect()

        try:
            if 'clients' in types:
                self.get_clients(registry, dev, dev.hostname)
            if 'cpu' in types:
                self.get_cpu(registry, dev, dev.hostname)
            if 'memory' in types:
                self.get_memory(registry, dev, dev.hostname)
            if 'system information' in types:
                self.get_system_information(registry, dev, dev.hostname)
            if 'access point statistics' in types:
                self.get_access_point_statistics(registry, dev, dev.hostname)
            if 'access point state' in types:
                self.get_access_point_state(registry, dev, dev.hostname)
        except (AttributeError) as e:
            print(e)
            dev.disconnect()
            return 500, "Device unreachable", "Device {} unreachable".format(dev.hostname)
        except (KeyError) as e:
            print(e)
            dev.disconnect()
            return 500, 'Device unreachable', "Device {} unreachable".format(dev.hostname)
        dev.disconnect()
        return 200, "OK", registry.collect()
