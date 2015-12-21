# -*- coding: utf-8 -*-

import sys
import logging

from ertza.drivers.Drivers import Driver


class MachineError(Exception):
    pass


class Machine(object):

    def __init__(self):
        # Ugly fix for circular dependency
        from ertza.drivers.Slave import Slave, SlaveMachine, SlaveMachineError

        self._Slave, self._SlaveMachine = Slave, SlaveMachine
        self._SlaveMachineError = SlaveMachineError

        self._SlaveMachine.machine = self

        self.version = None

        self.config = None
        self.driver = None
        self.cape_infos = None

        self.comms = {}
        self.processors = {}
        self.commands = None
        self.synced_commands = None
        self.unbuffered_commands = None

        self.slaves = []
        self.master = None
        self.slave_mode = None

    def init_driver(self):
        drv = self.config.get('machine', 'driver', fallback=None)
        logging.info("Loading %s driver" % drv)
        if drv is not None:
            try:
                driver_config = self.config['driver_' + drv]
            except KeyError:
                driver_config = {}
                logging.error("Unable to get config for %s driver" % drv)

            try:
                self.driver = Driver().get_driver(drv)(driver_config)
            except KeyError:
                logging.error("Unable to get %s driver, exiting." % drv)
                sys.exit()
        else:
            logging.error("Machine driver is not defined, aborting.")
            return False

        return drv

    def start(self):
        self.driver.connect()

    def exit(self):
        self.driver.exit()

        for n, c in self.comms.items():
            c.exit()

    def reply(self, command):
        if command.answer is not None:
            self.send_message(command.protocol, command.answer)

    def send_message(self, msg):
        self.comms[msg.protocol].send_message(msg)

    @property
    def infos(self):
        rev = self.cape_infos['revision'] if self.cape_infos \
            else '0000'
        var = self.config.variant.split('.')

        return ('identify', var[0].upper(), var[1].upper(), rev)

    @property
    def serialnumber(self):
        if not self.cape_infos:
            return False

        sn = self.cape_infos['serialnumber'] if self.cape_infos \
            else '000000000000'

        return sn

    @property
    def address(self):
        pass

    def search_slaves(self):
        slaves_cf = self.config['slaves']
        slaves = []

        for key, item in slaves_cf.items():
            if key.startswith('slave_serialnumber_'):
                slave_id = int(key.split('_')[2])
                slave_sn = item
                slave_ip = slaves_cf['slave_address_%d' % slave_id]
                slave_dv = slaves_cf.get('slave_driver_%d' % slave_id,
                                         fallback='Osc').title()

                slave_cf = {}
                if self.config.has_section('slave_%s' % slave_sn):
                    slave_cf = self.config['slave_%s' % slave_sn]

                s = self._Slave(slave_sn, slave_ip, slave_dv, slave_cf)
                logging.info('Found {2} slave at {1} '
                             'with S/N {0}'.format(*s))
                slaves.append(s)

        if not slaves:
            return False

        self.slaves = []
        for s in slaves:
            m = self._SlaveMachine(s)
            self.slaves.append(m)

        self.slaves = tuple(self.slaves)
        return self.slaves

    def load_slaves(self):
        if not self.slaves:
            if not self.search_slaves():
                logging.info('No slaves found')
                return

        for s in self.slaves:
            self.init_slave(s)
            if s.serialnumber != s.get_serialnumber():
                infos = s.slave + (s.get_serialnumber(),)
                raise MachineError('S/N don\'t match for {2} slave at {1} '
                                   '({0} vs {4})'.format(*infos))

    def add_slave(self, driver, address):
        try:
            s = self._Slave(None, address, driver.title(), {})
            m = self._SlaveMachine(s)
            self.init_slave(m)
            m.get_serialnumber()
            m.set_master(self.serialnumber, self.address(driver))

            existing_s = self.get_slave(m.serialnumber)
            if existing_s:
                raise MachineError('Already existing {2} at {1} '
                                   'with S/N {0}'.format(*existing_s.slave))

            self.slaves.append(m)
            s = m.slave
            logging.info('New {2} slave at {1} '
                         'with S/N {0}'.format(*s))
            return s
        except Exception as e:
            raise MachineError('Unable to add slave: %s' % repr(e))

    def remove_slave(self, sn):
        try:
            rm_slave = self.get_slave(sn)
            if not rm_slave:
                raise MachineError('Slave with S/N %s not found' % sn)

            slave_id, slave = rm_slave

            slave.unslave()
            slave.exit()
            slave_instance = self.slaves.pop(slave_id)
            del slave_instance
        except Exception as e:
            raise MachineError('Unable to remove slave: %s' % str(e))

    def get_slave(self, sn):
        for i, s in enumerate(self.slaves):
            if sn == s.slave.serialnumber:
                return i, s

    def init_slave(self, slave_machine):
        try:
            slave_machine.init_driver()
            slave_machine.start()
        except self._SlaveMachineError as e:
            raise MachineError('Couldn\'t initialize {2} slave at {1} '
                               'with S/N {0}: {exc}'.format(*slave_machine.slave,
                                                            exc=e))

    def set_slave_mode(self, mode=None):
        if mode:
            if mode not in ('master', 'slave'):
                raise MachineError('Unrecognized mode %s' % mode)

            if mode == 'master':
                if self.slave_mode == 'master':
                    raise MachineError('Master mode already activated')

                if not self.slaves:
                    raise MachineError('No slaves found')

                for s in self.slaves:
                    s.enslave()

        else:
            logging.info('Deactivating %s mode' % self.slave_mode)

            if mode == 'master':
                pass
