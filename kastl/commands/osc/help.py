# -*- coding: utf-8 -*-

from kastl.commands import UnbufferedCommand
from kastl.commands import OscCommand


class ListCommands(OscCommand, UnbufferedCommand):

    def execute(self, c):
        cmds = self.machine.processors['OSC'].available_commands
        for alias, cmd in cmds.items():
            try:
                self.reply(c, repr(cmd), cmd.help_text)
            except AttributeError:
                self.reply(c, repr(cmd))

        self.ok(c, 'done')

    @property
    def alias(self):
        return '/help/list'
