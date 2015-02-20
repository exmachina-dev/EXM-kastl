# -*- coding: utf-8 -*-

from ertza.base import BaseWorker
from ertza.remotes.osc import OSCServer
from ertza.remotes.modbus import ModbusMaster
import ertza.errors as err

import time

class RemoteWorker(BaseWorker):
    """
    Master process that handle all communication instances:
        - Discret I/Os
        - Accessories serial bus
        - LCD display
    """

    def __init__(self, sm):
        super(RemoteWorker, self).__init__(sm)
        self.config_pipe = self.initializer.conf_rmt_pipe[1]

        self.get_logger()
        self.lg.debug("Init of RemoteWorker")

        self.wait_for_config()

        self.run()

    def run(self):
        while not self.exit_event.is_set():
            time.sleep(self.interval)


class OSCWorker(BaseWorker):
    """
    Master process that handle OSCServer:
    """

    def __init__(self, sm):
        super(OSCWorker, self).__init__(sm)
        self.interval = 0.001

        self.config_pipe = self.initializer.conf_osc_pipe[1]

        self.get_logger()
        self.lg.debug("Init of OSCWorker")

        self.wait_for_config()
        self.run()

    def run(self):
        try:
            self.init_osc_server()
        except err.OSCServerError as e:
            self.lg.warn(e)
            self.exit_event.set()

        while not self.exit_event.is_set():
            self.osc_server.run(self.interval)
            if self.osc_event.is_set():
                self.lg.info('OSC server restarting…')
                self.init_osc_server(True)
                self.osc_event.clear()

            time.sleep(self.interval)

    def init_osc_server(self, restart=False):
        if restart:
            del self.osc_server
        self.osc_server = OSCServer(self.config_pipe, self.lg, self.osc_event)
        self.osc_server.start(blocking=False)


class ModbusWorker(BaseWorker):
    """
    Master process that handle ModbusBackend:
    """

    def __init__(self, sm):
        super(ModbusWorker, self).__init__(sm)
        self.interval = 0.001

        self.config_pipe = self.initializer.conf_mdb_pipe[1]

        self.get_logger()
        self.lg.debug("Init of ModbusWorker")

        self.wait_for_config()
        self.run()

    def run(self):
        try:
            self.init_modbus()
        except err.ModbusMasterError as e:
            self.lg.warn(e)
            self.exit_event.set()

        while not self.exit_event.is_set():
            self.modbus_master.run()
            if self.modbus_event.is_set():
                self.lg.info('Modbus master restarting…')
                self.init_modbus(True)
                self.modbus_event.clear()

            time.sleep(self.interval)

    def init_modbus(self, restart=False):
        if restart:
            del self.modbus_backend
        self.modbus_master = ModbusMaster(self.config_pipe, self.lg,
                self.modbus_event, self.blockall_event)
        self.modbus_master.start()


__all__ = ['RemoteWorker', 'OSCWorker', 'ModbusWorker']
