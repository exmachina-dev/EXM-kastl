# -*- coding: utf-8 -*-

import subprocess


class EthernetInterface(object):
    def __init__(self, interface):
        self.interface = interface

        self._macaddress = None
        self.update_table()

    def update_table(self):
        c = ['ip', 'addr', 'show', 'dev', self.interface]

        output = subprocess.check_output(c)
        r = [l.lstrip() for l in output.splitlines()]

        self._ips = []
        for line in r:
            if not line.startswith(b'inet '):
                del line
                continue

            self._ips.append(line.split()[1].decode())

    def add_ip(self, ip):
        try:
            ip_addr, ip_mask = ip.split('/')
            if len(ip_addr.split('.')) != 4:
                raise ValueError
        except ValueError:
            raise ValueError('Invalid format for IP address. Use CIDR notation')

        c = ['ip', 'addr', 'add', ip, 'dev', self.interface]
        try:
            subprocess.check_call(c)
        except subprocess.CalledProcessError as e:
            raise e
        finally:
            self.update_table()

    def del_ip(self, ip):
        try:
            ip_addr, ip_mask = ip.split('/')
            if len(ip_addr.split('.')) != 4:
                raise ValueError
        except ValueError:
            raise ValueError('Invalid format for IP address. Use CIDR notation')

        c = ['ip', 'addr', 'delete', ip, 'dev', self.interface]
        try:
            subprocess.check_call(c)
        except subprocess.CalledProcessError as e:
            raise e
        finally:
            self.update_table()

    def link_up(self):
        c = ['ip', 'link', 'set', 'dev', self.interface, 'up']
        subprocess.check_call(c)

    def link_down(self):
        c = ['ip', 'link', 'set', 'dev', self.interface, 'down']
        subprocess.check_call(c)

    @property
    def ips(self):
        return self._ips

    @property
    def mac_address(self):
        if self._macaddress:
            return self._macaddress
        c = ['ip', 'link', 'show', 'dev', self.interface]

        output = subprocess.check_output(c)
        r = [l.lstrip() for l in output.splitlines()]

        for line in r:
            if not line.startswith(b'link/ether '):
                del line
                continue

            self._macaddress = line.split()[1].decode()
            return self._macaddress
