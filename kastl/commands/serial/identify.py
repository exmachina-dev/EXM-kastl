# -*- coding: utf-8 -*-

import logging

from kastl.commands import BufferedCommand
from kastl.commands import SerialCommand


class Identify(SerialCommand, BufferedCommand):

    def execute(self, c):
        logging.info('Found remote with S/N {}'.format(c.serial_number))
        data = ('identify', self.machine.serialnumber)
        self.send(*data)

    @property
    def alias(self):
        return 'identify'
