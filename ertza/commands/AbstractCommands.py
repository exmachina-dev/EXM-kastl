# -*- coding: utf-8 -*-


class AbstractCommand(object):

    def __init__(self, machine):
        self.machine = machine
        self.eventReady = None

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
