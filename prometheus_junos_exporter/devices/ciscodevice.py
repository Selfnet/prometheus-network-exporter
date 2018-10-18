from ydk.services import CRUDService
from ydk.providers import NetconfServiceProvider
from ydk.models.cisco_ios_xr import Cisco_IOS_XR_shellutil_oper \
    as xr_shell
from datetime import timedelta
from prometheus_junos_exporter.devices import basedevice


class CiscoNetworkDevice(basedevice.Device):
    def __init__(self, hostname, user=None, password=None, port=22, ssh_private_key_file=None, ssh_config=None):
        # create NETCONF session
        self.device = NetconfServiceProvider(address=hostname,
                                          port=port,
                                          username=user,
                                          password=password,
                                          protocol="ssh")
        # create CRUD service
        crud = CRUDService()

        # create system time object
        system_time = xr_shell.SystemTime()

        # read system time from device
        system_time = crud.read(self.device, system_time)

        # print system uptime
        print("System uptime is " +
              str(timedelta(seconds=system_time.uptime.uptime)))



class CiscoMetrics(basedevice.Metrics):
    def metrics(self, types, dev, registry):
        pass

if __name__ == '__main__':
    dev = CiscoNetworkDevice(hostname="129.143.74.1", user="root", password="root")