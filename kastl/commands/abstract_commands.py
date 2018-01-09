# -*- coding: utf-8 -*-

import operator


class AbstractCommand(object):

    def __init__(self, machine):
        self.machine = machine
        self.event_ready = None

    def execute(self, command):
        """
        Python code to execute when receiving this command.
        """
        raise NotImplementedError

    def send(self, command):
        """
        This method should implement a quick an simple way to send a message
        via the subclass.
        """
        raise NotImplementedError

    def check_args(self, c, comp_op='eq', v=1, reply=True):
        op = getattr(operator, comp_op)
        comp = op(len(c.args), v)
        if not comp and reply:
            self.error(c, 'Invalid number of arguments for %s (%d %s %d: %s)' % (
                self.alias, len(c.args), comp_op, v, ' '.join(map(str, c.args))))

        return comp

    @property
    def alias(self):
        """
        This should return an identifier for the processor.
        i.e:
            /path for OSC
        """
        raise NotImplementedError

    @property
    def buffered(self):
        """
        This method should be overrided if the command has to be buffered.
        """
        return False

    @property
    def synced(self):
        """
        This method should be overrided if the command has to be synced.
        """
        return False

    @property
    def help_text(self):
        """
        This method should be overrided to provide a help text.
        """
        raise AttributeError

    def __repr__(self):
        if hasattr(self, 'args'):
            return '{0.alias} {0.args}'.format(self)
        else:
            return self.alias


class UnbufferedCommand(AbstractCommand):
    pass


class BufferedCommand(AbstractCommand):

    @property
    def buffered(self):
        return True


class SyncedCommand(AbstractCommand):

    @property
    def synced(self):
        return True
