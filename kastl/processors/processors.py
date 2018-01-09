# -*- coding: utf-8 -*-

import logging

from .abstract_processor import AbstractProcessor

from ..commands import OscCommand, SerialCommand

logging = logging.getLogger('kastl.processors')


class OscProcessor(AbstractProcessor):

    def __init__(self, machine):
        super().__init__("commands.osc", OscCommand, machine)

        osc_cmds = ' '.join(self.available_commands)
        logging.info("OSC commands loaded: %s" % osc_cmds)


class SerialProcessor(AbstractProcessor):

    def __init__(self, machine):
        super().__init__("commands.serial", SerialCommand, machine)

        serial_cmds = ' '.join(self.available_commands)
        logging.info("Serial commands loaded: %s" % serial_cmds)
