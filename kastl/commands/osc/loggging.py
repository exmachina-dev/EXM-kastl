# -*- coding: utf-8 -*-

import logging

from kastl.commands import UnbufferedCommand
from kastl.commands import OscCommand

from kastl.processors.osc import OscAddress


class OscLogHandler(logging.Handler):

    def __init__(self, machine, target, port=None):
        self.machine = machine
        self._target = OscAddress(hostname=target, port=port)

        super().__init__()

    def emit(self, record):
        try:
            self.send(self._target, '/log/entry', self.format(record),
                      msg_type='log')
        except Exception:   # This a log handler, we forgive everything
            pass


class LogTo(OscCommand, UnbufferedCommand):

    def execute(self, c):
        if len(c.args) == 2:
            log_ip, log_port = c.args
        else:
            log_ip, log_port = c.args[0], None
        self.machine.osc_loghandler = OscLogHandler(self.machine, log_ip, log_port)
        root_log = logging.getLogger()
        root_log.addHandler(self.machine.osc_loghandler)
        self.ok(c, 'Binding OSC log handler to %s:%s' % (log_ip, str(log_port)))

    @property
    def alias(self):
        return '/log/to'


class LogLevel(OscCommand, UnbufferedCommand):

    def execute(self, c):
        if not self.check_args(c, 'eq', 1):
            return

        try:
            level, = c.args
            self.machine.osc_loghandler.setLevel(int(level))
        except AttributeError:
            self.error(c, 'OSC log handler is not specified. '
                       'Run /log/to target prior to this command')
        except Exception as e:
            self.error(c, 'Error while setting loglevel: {!r}'.format(e))

    @property
    def alias(self):
        return '/log/level'


class LogStop(OscCommand, UnbufferedCommand):

    def execute(self, c):
        try:
            root_log = logging.getLogger()
            root_log.removeHandler(self.machine.osc_loghandler)
            self.ok(c, 'Stopped log forwarding')
        except AttributeError:
            self.error(c, 'OSC log handler is not specified. '
                       'Run /log/to target prior to this command')
        except Exception as e:
            self.error(c, 'Error while setting loglevel: {!r}'.format(e))

    @property
    def alias(self):
        return '/log/stop'
