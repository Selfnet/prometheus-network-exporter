import pwd
import os
import re
import glob
import ipaddress
import socket
import struct
import codecs


PROC_TCP = "/proc/net/tcp"
PROC_TCP6 = "/proc/net/tcp6"
STATE = {
    '01': 'ESTABLISHED',
    '02': 'SYN_SENT',
    '03': 'SYN_RECV',
    '04': 'FIN_WAIT1',
    '05': 'FIN_WAIT2',
    '06': 'TIME_WAIT',
    '07': 'CLOSE',
    '08': 'CLOSE_WAIT',
    '09': 'LAST_ACK',
    '0A': 'LISTEN',
    '0B': 'CLOSING'
}


def lookup(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, OSError):
        return ip


def _load(v4=None, v6=None):
    ''' Read the table of tcp connections & remove header  '''
    if not v4 and v6:
        with open(PROC_TCP6, 'r') as f:
            content = f.readlines()
            content.pop(0)
        return content
    elif v4 and not v6:
        with open(PROC_TCP, 'r') as f:
            content = f.readlines()
            content.pop(0)
        return content
    elif v4 and v6:
        raise Exception("Only IPv4 or IPv6 not both!")
    else:
        raise Exception("Specify IPv4 or IPv6!")


def _hex2dec(s):
    return str(int(s, 16))


def ipv4(addr):
    addr = int(addr, 16)
    addr = struct.pack('<I', addr)
    addr = socket.inet_ntop(socket.AF_INET, addr)
    return str(ipaddress.ip_address(addr))


def ipv6(addr):
    addr = codecs.decode(addr, 'hex')
    addr = struct.unpack('>IIII', addr)
    addr = struct.pack('@IIII', *addr)
    addr = socket.inet_ntop(socket.AF_INET6, addr)
    return str(ipaddress.ip_address(addr))


def _ip(s):
    if len(s) == 8:
        return ipv4(s)
    elif len(s) == 32:
        return ipv6(s)


def _remove_empty(array):
    return [x for x in array if x != '']


def _convert_ip_port(array):
    host, port = array.split(':')
    return _ip(host), _hex2dec(port)


def netstat(v4=None, v6=None):
    '''
    Function to return a list with status of tcp connections at linux systems
    To get pid of all network process running on system, you must run this script
    as superuser
    '''

    content = _load(v4=v4, v6=v6)
    for line in content:
        # Split lines and remove empty spaces.
        line_array = _remove_empty(line.split(' '))
        # Convert ipaddress and port from hex to decimal.
        l_host, l_port = _convert_ip_port(line_array[1])
        r_host, r_port = _convert_ip_port(line_array[2])
        tcp_id = line_array[0]
        state = STATE[line_array[3]]
        uid = pwd.getpwuid(int(line_array[7]))[0]       # Get user from UID.
        # Need the inode to get process pid.
        # inode = line_array[9]
        # pid = _get_pid_of_inode(inode)                  # Get pid prom inode.
        # try:                                            # try read the process name.
        #     exe = os.readlink('/proc/'+pid+'/exe')
        # except:
        #     exe = None
        nline = {'id': tcp_id, 'uid': uid, 'local_host': l_host, 'local_port': int(
            l_port), 'remote_host': r_host, 'remote_port': int(r_port), 'state': state, 'executable': None}
        yield nline


def ssh(v4=None, v6=None):
    for conn in netstat(v4=v4, v6=v6):
        if conn['remote_port'] in [22]:
            yield conn


def http(v4=None, v6=None):
    for conn in netstat(v4=v4, v6=v6):
        if conn['remote_port'] in [80, 443, 8080, 8443, 4343]:
            yield conn


def _get_pid_of_inode(inode):
    '''
    To retrieve the process pid, check every running process and look for one using
    the given inode.
    '''
    for item in glob.glob('/proc/[0-9]*/fd/[0-9]*'):
        try:
            if re.search(inode, os.readlink(item)):
                return item.split('/')[2]
        except:
            pass
    return None
