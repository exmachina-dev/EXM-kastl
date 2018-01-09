# -*- coding: utf-8 -*-

import logging

from .abstract_machinemode import AbstractMachineMode, ContinueException

logging = logging.getLogger('kastl.machine.modes.standalone')


class StandaloneMachineMode(AbstractMachineMode):
    _param = AbstractMachineMode._param

    def __init__(self, machine):
        super().__init__(machine)

        try:
            drv_attr_map = self._machine.driver.get_attribute_map()
            logging.debug('Appending driver attribute map '
                          'to {0.__class__.__name__}'.format(self))
            for a, p in drv_attr_map.items():
                StandaloneMachineMode.MachineMap.update({
                    '{}'.format(a): self._param(*p),
                })

        except AttributeError:
            pass

    def __getitem__(self, key):
        try:
            res = super().__getitem__(key)
        except ContinueException:
            if key in self.StaticKeys:
                res = self._last_values.get(key, None)
                if res is None:
                    res = self._machine.driver[key]
            else:
                res = self._machine.driver[key]

        return res

    def __setitem__(self, key, value):
        try:
            super().__setitem__(key, value)
        except ContinueException:
            self._machine.driver[key] = value

        if key in self.StaticKeys:
            self._last_values[key] = value
