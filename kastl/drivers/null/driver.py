# -*- coding: utf-8 -*-

import logging

from ..abstract_driver import AbstractDriver, AbstractDriverError
from ..frontend import DriverFrontend
from ..netdata_maps import MicroflexE100Map

logging = logging.getLogger('kastl.drivers.null')


class NullDriverError(AbstractDriverError):
    def __init__(self, exception=None):
        self._parent_exception = exception

    def __repr__(self):
        if self._parent_exception:
            return '{0.__class__.__name__}: {0._parent_exception!r}'.format(self)


class ReadOnlyError(NullDriverError, IOError):
    def __init__(self, key):
        super().__init__('%s is read-only' % key)


class WriteOnlyError(NullDriverError, IOError):
    def __init__(self, key):
        super().__init__('%s is write-only' % key)


class NullDriver(AbstractDriver):
    def __init__(self, config):

        self.config = config

        self.netdata_map = MicroflexE100Map
        self._prev_data = {}

        self.connected = None

        self.fake_data = {}

        self.frontend = DriverFrontend()

    def connect(self):
        if not self.connected:
            self.connected = True
        self.connected = True

    def exit(self):
        self['command:enable'] = False

    def get_attribute_map(self):
        attr_map = {}
        for a, p in self.netdata_map.items():
            if isinstance(p, dict):
                for sa, sp in p.items():
                    attr_map.update({'{}:{}'.format(a, sa): (sp.vtype, sp.mode,)})
            else:
                attr_map.update({a: (p.vtype, p.mode,)})

        return attr_map

    def send_default_values(self):
        for key in self.frontend.DEFAULTS_KEYS:
            try:
                self[key] = self.frontend[key]
            except KeyError as e:
                logging.error('{!s}'.format(e))

    def __getitem__(self, key):
        try:
            if len(key.split(':')) == 2:
                seckey, subkey = key.split(':')
            else:
                seckey, subkey = key, None

            if seckey not in self.netdata_map:
                raise KeyError(seckey)

            if type(self.netdata_map[seckey]) == dict:
                if subkey:
                    if subkey not in self.netdata_map[seckey]:
                        raise KeyError(subkey)
                    ndk = self.netdata_map[seckey][subkey]
                else:
                    return [(sk, self._get_value(self.netdata_map[seckey][sk], key),)
                            for sk in self.netdata_map[seckey].keys()]
            else:
                ndk = self.netdata_map[seckey]

            return self._get_value(ndk, seckey, sub=subkey)
        except Exception as e:
            logging.error('Got exception in {!r}: {!r}'.format(self, e))
            raise NullDriverError(e)

    def __setitem__(self, key, value):
        if len(key.split(':')) == 2:
            seckey, subkey = key.split(':')
        else:
            seckey, subkey = key, None

        if seckey not in self.netdata_map:
            raise KeyError('Unable to find {} in netdata map'.format(seckey))

        if type(self.netdata_map[seckey]) == dict and subkey:
            if subkey not in self.netdata_map[seckey]:
                raise KeyError('Unable to find {0} in {1} '
                               'netdata map'.format(subkey, seckey))
            pndk = self.netdata_map[seckey]
            ndk = self.netdata_map[seckey][subkey]
            seclen = len(self.netdata_map[seckey])

            if seckey not in self._prev_data.keys():
                self._prev_data[seckey] = {}

            forget_values = ('cancel', 'reset', 'go', 'set_home', 'go_home', 'stop')
            unique_values = ('control_mode',)
            data = list((-1,) * seclen)

            for k, cndk in pndk.items():
                data[cndk.start] = self._prev_data[seckey].get(k, cndk.vtype(0))
            data[ndk.start] = ndk.vtype(value)

            for k, cndk in pndk.items():
                if k == subkey and subkey in unique_values:
                    try:
                        if ndk.vtype(value) == self._prev_data[seckey][k]:
                            return
                    except KeyError:
                        pass
                elif ndk.start != cndk.start:
                    if k in forget_values:
                        data[cndk.start] = cndk.vtype(0)
                        self._prev_data[seckey][k] = cndk.vtype(0)
                    if k in unique_values:
                        data[cndk.start] = cndk.vtype(0)

            self._prev_data[seckey][subkey] = ndk.vtype(value)
        else:
            ndk = self.netdata_map[seckey]
            data = (self.frontend.output_value(key, ndk.vtype(value)),)

        if 'w' not in ndk.mode:
            raise WriteOnlyError(key)

        return self.write_fake_data(seckey, data, sub=subkey)

    def _get_value(self, ndk, key, sub=None):
        st, vt, md = ndk.start, ndk.vtype, ndk.mode

        if 'r' not in md:
            raise ReadOnlyError(key)

        res = self.read_fake_data(key, sub=sub)
        if not res:
            return

        return self.frontend.input_value(key, vt(res[st]))

    def write_fake_data(self, key, data, sub=None):
        if sub is not None:
            try:
                self.fake_data[key][sub] = data
            except KeyError:
                self.fake_data[key] = {sub: data, }

            if key == 'command' and sub in ('cancel', 'drive_enable', 'stop'):
                self.fake_data['velocity'] = (0,)
        else:
            self.fake_data[key] = data
            if key == 'velocity_ref':
                self.fake_data['velocity'] = data

    def read_fake_data(self, key, sub=None):
        if sub is not None:
            try:
                return self.fake_data[key][sub]
            except KeyError:
                if key == 'status':
                    return False
                else:
                    logging.debug('Unrecognized key: {}:{}'.format(key, sub))
                    return None
        else:
            try:
                return self.fake_data[key]
            except KeyError:
                logging.debug('Unrecognized key: {}'.format(key))
                return None
