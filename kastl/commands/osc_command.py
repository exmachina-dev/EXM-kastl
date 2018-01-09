# -*- coding: utf-8 -*-

from ..processors.osc import OscMessage
from .abstract_commands import AbstractCommand


class OscCommand(AbstractCommand):
    SEP = '/'

    def send(self, target, path, *args, **kwargs):
        if args and isinstance(args[0], (list, tuple)):
            args = args[0]

        m = OscMessage(path, *args, receiver=target, **kwargs)
        return self.machine.send_message(m)

    def ok(self, command, *args, **kwargs):
        return self.reply(command, *args, add_path='/ok', **kwargs)

    def error(self, command, *args, **kwargs):
        args = [str(a) if isinstance(a, Exception) else a for a in args]
        return self.reply(command, *args, add_path='/error', **kwargs)

    def reply(self, command, *args, **kwargs):
        add_path = kwargs.pop('add_path', None)
        if add_path:
            if not isinstance(add_path, str):
                raise TypeError('add_path kwarg must be a string')
            full_path = self.alias + add_path if add_path.startswith(self.SEP) \
                else '{0.alias}{0.SEP}{1}'.format(self, add_path)
        else:
            full_path = self.alias

        return self.send(command.sender, full_path, *args, **kwargs)
