# -*- coding: utf-8 -*-

from ..processors.serial import SerialMessage
from .abstract_commands import AbstractCommand


class SerialCommand(AbstractCommand):
    SEP = '.'

    def send(self, *args, **kwargs):
        m = kwargs['msg'] if 'msg' in kwargs else \
            SerialMessage()

        for d in args:
            m.cmd_bytes += d

        return self.machine.send_message(m)

    def ok(self, command, *args, **kwargs):
        self.reply(command, *args, add_path='.ok', **kwargs)

    def error(self, command, *args, **kwargs):
        self.reply(command, *args, add_path='.error', **kwargs)

    def reply(self, command, *args, **kwargs):
        if 'add_path' in kwargs:
            if not isinstance(kwargs['add_path'], str):
                raise TypeError('add_path kwarg must be a string')
            full_path = self.alias + kwargs['add_path'] \
                if kwargs['add_path'].startswith(self.SEP) \
                else '{0.alias}{0.SEP}{1[add_path]}'.format(self, kwargs)
        else:
            full_path = self.alias

        self.send(full_path, *args, **kwargs)
