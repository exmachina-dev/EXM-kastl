# -*- coding: utf-8 -*-

import logging
from collections import namedtuple

from ertza.Machine import Machine
from ertza.drivers.Drivers import Driver
from ertza.drivers.AbstractDriver import AbstractDriverError


Slave = namedtuple('Slave', ('serialnumber', 'address', 'driver', 'config'))


class SlaveMachineError(AbstractDriverError):
    pass


class SlaveMachine(Machine):

    machine = None

    def __init__(self, slave):

        self.config = slave.config
        self.driver = None

        self.slave = slave

        self.driver_config = {
            'target_address': self.slave.address,
            'target_port': int(self.config.get('reply_port', 6969)),
        }

    def init_driver(self):
        drv = self.slave.driver
        logging.info("Loading %s driver" % drv)
        if drv is not None:
            try:
                driver = Driver().get_driver(drv)
                self.driver = driver(self.driver_config, self.machine)
                self.inlet = self.driver.init_pipe()
            except KeyError:
                logging.error("Unable to get %s driver, aborting." % drv)
                return
            except AbstractDriverError as e:
                raise SlaveMachineError('Unable to intialize driver: %s' % e)
        else:
            logging.error("Machine driver is not defined, aborting.")
            return False

        return drv

    def exit(self):
        self.driver.exit()

    @property
    def infos(self):
        rev = self.driver['machine:revision']
        try:
            var = self.driver['machine:variant'].split('.')
        except AttributeError:
            var = 'none:none'

        return (self.serialnumber, var[0].upper(), var[1].upper(), rev)

    @property
    def serialnumber(self):
        return self.slave.serialnumber

    def get_serialnumber(self):
        return self.driver['serialnumber']
