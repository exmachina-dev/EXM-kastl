# -*- coding: utf:8 -*-
import sys

class ErtzaError(Exception):
    """Base class for Ertza exceptions."""

    def __init__(self, msg=''):
        self.message = msg
        Exception.__init__(self, msg)

    def __repr__(self):
        return self.message

    __str__ = __repr__


class FatalError(ErtzaError):
    """Raised when program cannot continue."""

    def __init__(self, msg=''):
        Error.__init__(self, 'Fatal: %s' % (msg,))


class TimeoutError(ErtzaError):
    """Raised on a function timeout."""

    def __init__(self, msg=''):
        Error.__init__(self, 'Timeout: %s' % (msg,))


class ConfigError(FatalError):
    """Raised when program cannot load config."""

    def __init__(self, msg=''):
        FatalError.__init__(self, 'Unable to load config: %s' % (msg,))


class OSCServerError(FatalError):
    """Raised when program cannot start OSC server."""

    def __init__(self, msg=''):
        FatalError.__init__(self, 'Cannot start OSC server: %s' % (msg,))


class SlaveError(FatalError):
    """Raised in Slave server."""

    def __init__(self, msg=''):
        FatalError.__init__(self, 'Slave error: %s' % (msg,))


class SerialError(FatalError):
    """Raised when program cannot start OSC server."""

    def __init__(self, msg=''):
        FatalError.__init__(self, 'SerialError: %s' % (msg,))


class ModbusMasterError(FatalError):
    """Raised when program cannot start Modbus master."""

    def __init__(self, msg=''):
        Error.__init__(self, 'Cannot start Modbus master: %s' % (msg,))
