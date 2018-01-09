# -*- coding: utf-8 -*-

from enum import Enum, unique
from threading import Event
from queue import Queue

from .types import MachineType
from .control_mode import ControlMode


class AbstractMachineError(Exception):
    pass


class AbstractFatalMachineError(AbstractMachineError):
    pass


@unique
class MotionModes(Enum):
    VELOCITY = 1
    POSITION = 2
    TORQUE = 3
    ENHANCED_TORQUE = 4


class AbstractMachine(object):

    def __init__(self):
        self.machine_type = MachineType.NONE
        self.machine_class = None
        self.control_mode = ControlMode.NONE

        self._serialnumber = None
        self._ip_address = None
        self._port = None

        self._version = None
        self._control_mode = None

        self.config = None          # Machine specific config
        self.driver = None          # Driver for communication with the machine

        self.fatal_error_ev = Event()   # A fatal error that will stop the movement
        self.warning_ev = Event()       # A warning issued by the attached machine
        self.timeout_ev = Event()       # A timeout occured
        self.running_ev = Event()

        self.messages_queue = Queue()

    def init_communication(self):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def reply(self, command):
        raise NotImplementedError

    def send_message(self, msg):
        raise NotImplementedError

    @property
    def serialnumber(self):
        return self._serialnumber

    @property
    def ip_address(self):
        return self._ip_address
