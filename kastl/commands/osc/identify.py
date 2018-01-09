# -*- coding: utf-8 -*-

from kastl.commands import BufferedCommand
from kastl.commands import OscCommand


class Identify(OscCommand, BufferedCommand):

    def execute(self, c):
        self.ok(c, self.machine.serialnumber, self.machine.osc_address)

    @property
    def alias(self):
        return '/identify'


class Version(OscCommand, BufferedCommand):

    def execute(self, c):
        version = self.machine.version
        self.ok(c, version)

    @property
    def alias(self):
        return '/version'
