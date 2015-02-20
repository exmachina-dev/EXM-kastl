# -*- coding: utf-8 -*-

import time
import logging
import logging.handlers


class BaseWorker(object):
    """
    Base worker for multiprocessing.Manager()
    """

    interval = 0.5

    def __init__(self, sm):
        self.initializer = sm
        self.sm = sm.manager
        self.lgq = sm.log_queue

        # Some events
        self.exit_event = sm.exit_event
        self.config_event = sm.config_event
        self.osc_event = sm.osc_event
        self.modbus_event = sm.modbus_event
        self.blockall_event = sm.blockall_event

        self.config_lock = sm.config_lock
        self.init_lock = sm.init_lock

        self.running = True

    def get_logger(self, name=__name__):
        _h = logging.handlers.QueueHandler(self.lgq) # Just the one handler needed
        self.lg = logging.getLogger(name)
        self.lg.addHandler(_h)
        self.lg.setLevel(logging.DEBUG)

    def run(self):
        pass

    def wait_for_config(self):
        while not self.config_event.is_set():
            time.sleep(self.interval)


class BaseCommunicationObject(object):
    _methods = {
            'get': 0x001,
            'set': 0x002,
            'dump': 0x003,
            'get_status': 0x004,
            'get_command': 0x005,
            'set_command': 0x006,
            }

    def __init__(self, target, *args):
        self.target = target
        self.method = None
        self.value = None

        if args:
            self.args = args
        else:
            self.args = None

    def send(self):
        if self.method:
            return self.target.send(self)
        else:
            raise ValueError("Method isn't defined.")

    def __str__(self):
        return '%s %s %s' % (self.method, self.args, self.value)

    __repr__ = __str__


class BaseRequest(BaseCommunicationObject):
    def send(self):
        super(BaseRequest, self).send()
        rp = self.target.recv()
        return rp

class BaseResponse(BaseCommunicationObject):
    pass
