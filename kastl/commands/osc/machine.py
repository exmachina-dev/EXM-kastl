# -*- coding: utf-8 -*-

from kastl.commands import UnbufferedCommand
from kastl.commands import OscCommand


class ListSlaves(OscCommand, UnbufferedCommand):

    def execute(self, c):
        if not self.machine.slaves:
            self.error(c, 'Machine has no slaves')
            return

        slaves = [s.slave for s in self.machine.slaves]

        self.reply(c, *slaves)

    @property
    def alias(self):
        return '/machine/slaves'


class AddSlave(OscCommand, UnbufferedCommand):

    def execute(self, c):
        if self.check_args(c, 'ne', 3):
            self.error(c, 'Invalid number of arguments for %s' % self.alias)
            return

        try:
            driver, address, mode = c.args
            n_slave = self.machine.add_slave(driver, address, mode)
            self.ok(c, n_slave.driver, n_slave.address, n_slave.serialnumber, n_slave.slave_mode)
        except Exception as e:
            self.error(c, e)

    @property
    def alias(self):
        return '/machine/slave/add'


class RemoveSlave(OscCommand, UnbufferedCommand):

    def execute(self, c):
        if self.check_args(c, 'ne', 1):
            return

        try:
            sn = c.args
            self.machine.remove_slave(sn)
            self.ok(c)
        except Exception as e:
            self.error(c, e)

    @property
    def alias(self):
        return '/machine/slave/remove'


class SlaveMode(OscCommand, UnbufferedCommand):

    def execute(self, c):
        if not self.check_args(c, 'eq', 1):
            return

        try:
            k, = c.args
            v = self.machine[k]
            self.ok(c, k, v)
        except Exception as e:
            self.error(c, e)

    @property
    def alias(self):
        return '/machine/slave/mode'


class MachineSet(OscCommand, UnbufferedCommand):

    def execute(self, c):
        if len(c.args) < 2:
            self.error(c, 'Invalid number of arguments for %s' % self.alias)
            return

        try:
            k, v, = c.args
            self.machine[k] = v
            self.ok(c, k, v)
        except Exception as e:
            self.error(c, k, str(e))

    @property
    def alias(self):
        return '/machine/set'


class MachineGet(OscCommand, UnbufferedCommand):

    def execute(self, c):
        if not self.check_args(c, 'eq', 1):
            return

        try:
            k, = c.args
            v = self.machine[k]
            self.ok(c, k, v)
        except Exception as e:
            self.error(c, k, str(e))

    @property
    def alias(self):
        return '/machine/get'
