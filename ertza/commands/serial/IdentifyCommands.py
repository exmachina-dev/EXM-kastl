# -*- coding: utf-8 -*-

import logging

from ertza.commands.AbstractCommands import BufferedCommand
from ertza.commands.SerialCommand import SerialCommand

from ertza.processors.serial.Serial import SerialMessage


class Identify(SerialCommand, BufferedCommand):

    def execute(self, c):
        infos = self.c.args + (self.c.data['serial_number'],)
        logging.info('Found %s %s with S/N %s' % infos)
        msg = SerialMessage(('identify', 'Armaz:%s:%s' % (
            self.machine.config.variant, self.machine.config.revision)))
        self.machine.send_message(c.protocol, msg)

    @property
    def alias(self):
        return 'identify'
