# -*- coding: utf-8 -*-

import logging

from ertza.commands.AbstractCommands import UnbufferedCommand
from ertza.commands.OscCommand import OscCommand

from ertza.processors.osc.Osc import OscMessage


class ConfigSet(OscCommand, UnbufferedCommand):

    def execute(self, c):
        if len(c.args) < 3:
            msg = OscMessage('/config/error',
                             ('Missing arguments for %s' % self.alias,),
                             receiver=c.sender)
            self.machine.send_message(c.protocol, msg)
            return
        sec, opt, val, = c.args
        msg = OscMessage('/config/info',
                         ('Setting [%s] %s to %s' % (sec, opt, val),),
                         receiver=c.sender)
        self.machine.send_message(c.protocol, msg)

        try:
            self.machine.config.set(sec, opt, val)
        except:
            msg = OscMessage('/config/error',
                             ('Unable to set [%s] %s to %s' % (sec, opt, val),),
                             receiver=c.sender)
            self.machine.send_message(c.protocol, msg)

    @property
    def alias(self):
        return '/config/set'


class ConfigGet(OscCommand, UnbufferedCommand):

    def execute(self, c):
        if len(c.args) != 2:
            msg = OscMessage('/config/error',
                             ('Invalid number of arguments for %s' % self.alias,),
                             receiver=c.sender)
            self.machine.send_message(c.protocol, msg)
            return
        sec, opt = c.args

        try:
            val = self.machine.config.get(sec, opt)
            msg = OscMessage('/config/get/%s/%s' % (sec, opt), (val,),
                             receiver=c.sender)
            self.machine.send_message(c.protocol, msg)
        except:
            msg = OscMessage('/config/error',
                             ('Unable to get [%s] %s' % (sec, opt),),
                             receiver=c.sender)
            self.machine.send_message(c.protocol, msg)

    @property
    def alias(self):
        return '/config/get'
