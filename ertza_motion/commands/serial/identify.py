# -*- coding: utf-8 -*-

import logging

from ertza.commands import BufferedCommand
from ertza.commands import SerialCommand


class Identify(SerialCommand, BufferedCommand):

    def execute(self, c):
        logging.info('Found remote with S/N {}'.format(c.serial_number))
        data = ('identify', self.machine.serialnumber)
        self.send(*data)

    @property
    def alias(self):
        return 'identify'
