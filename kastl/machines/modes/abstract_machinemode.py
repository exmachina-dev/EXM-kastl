# -*- coding: utf-8 -*-

import logging
from collections import namedtuple

logging = logging.getLogger('kastl.machine.modes')


class ContinueException(BaseException):
    pass


class MachineModeException(Exception):
    pass


class AbstractMachineMode(object):
    _param = namedtuple('parameter', ['vtype', 'mode'])

    MachineMap = {
        'operating_mode':   _param(str, 'rw'),
        'serialnumber':     _param(str, 'r'),
        'osc_address':          _param(str, 'r'),
        'ip_address':       _param(str, 'rw'),
    }

    DirectAttributesGet = (
        'serialnumber',
        'operating_mode',
        'infos',
        'osc_address',
        'ip_address'
    )

    DirectAttributesSet = (
        'ip_address'
    )

    StaticKeys = (
        'acceleration',
        'deceleration',
        'torque_rise_time',
        'torque_fall_time',
        'entq_kp',
        'entq_kp_vel',
        'entq_ki',
        'entq_kd',
    )

    def __init__(self, machine):
        self._machine = machine
        self._last_values = {}

    def _check_read_access(self, key):
        self._check_key(key)
        if 'r' not in self.MachineMap[key].mode:
            raise KeyError('{} is not readable'.format(key))

    def _check_write_access(self, key):
        self._check_key(key)
        if 'w' not in self.MachineMap[key].mode:
            raise KeyError('{} is not writable'.format(key))

    def _check_key(self, key):
        if key not in self.MachineMap.keys():
            raise KeyError('{0} not in {1.__class__.__name__} keys'.format(key, self))

    def __getitem__(self, key):
        self._check_read_access(key)

        if key in self.DirectAttributesGet:
            return self._machine.getitem(key)

        raise ContinueException()

    def __setitem__(self, key, value):
        self._check_write_access(key)

        if key == 'operating_mode':
            if isinstance(value, (list, tuple)):
                return self._machine.set_operating_mode(*value)
            else:
                return self._machine.set_operating_mode(value)

        if key in self.DirectAttributesSet:
            return self._machine.setitem(key)

        raise ContinueException()
