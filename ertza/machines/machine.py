# -*- coding: utf-8 -*-

import sys
import time
import logging

from threading import Event, Thread, Lock
import queue

from .abstract_machine import AbstractMachine

from .exceptions import MachineError, FatalMachineError
from .exceptions import MachineCommunicationTimeout

from .types import MachineType, get_machine_type, get_machine_class
from .modes import StandaloneMachineMode
from .modes import MasterMachineMode
from .modes import SlaveMachineMode
from .control_mode import ControlMode

from ..drivers import get_driver
from ..drivers import AbstractDriverError

from ..processors.osc import OscAddress, OscMessage

from .slave import Slave, SlaveMachine
from .slave import SlaveMachineError, FatalSlaveMachineError, SlaveRequest

from ..drivers.utils import retry

from ..configparser import parameter as _p
from ..configparser import _ChainMap as ChainMap

logging = logging.getLogger('ertza.machine')


OPERATING_MODES = ('standalone', 'master', 'slave')


class OscMachine(AbstractMachine):
    def __init__(self, *args, **kwargs):
        super().__init__()

        try:
            self._serialnumber = kwargs.pop('serialnumber', None)
            self._ip_address = kwargs.pop('ip_address')
            self._port = int(kwargs.pop('port'))
            self._target = OscAddress(hostname=self.ip_address,
                                 port=self.port)
        except KeyError as e:
            logging.error('Missing required key: %s', e.args[0])
            raise FatalMachineError('Missing required key: %s' % e.args[0])

        self.config = kwargs.pop('config', ChainMap())
        self.version = None
        self.control_mode = ControlMode.Velocity

        self.waiting_futures = list()
        self.driver = None
        self.refresh_interval = 0.25

        self._comms_thread = None
        self._machine_thread = None
        self._local_status = dict()

        self.last_command_time = time.time()

        self.init_communication()

    def init_communication(self):
        drv = 'Osc'
        if self.serialnumber:
            drv = self.config.get('driver', fallback='Osc')

        driver_config = {
            'target_address': self.ip_address,
            'target_port': self.port,
        }

        try:
            self.driver = get_driver(drv)(driver_config)
        except KeyError:
            e = MachineFatalError('Unable to get %s driver for %s.' % (drv, self.serialnumber))
            logging.exception(e)
            raise e

        logging.debug("%s driver loaded for %s" % (drv, self.serialnumber))
        return drv

    init_driver = init_communication

    def start(self):
        if self.connect():
            self.send_configuration()

    def connect(self):
        self._thread = Thread(target=self._communication_loop)
        self._thread.daemon = True
        self._thread.start()

        try:

            def cb(msg):
                if len(msg.result.args):
                    self.version = msg.result.args[0]

            f = self.send('/version')
            f.set_callback(cb)

            def cb(msg):
                if len(msg.result.args):
                    print(msg.result.args)
                    self.variant = str(msg.result.args[1])
                    self.machine_type = get_machine_type(self.variant)

            f = self.send('/config/get', 'machine:variant')
            f.set_callback(cb)


            print(f)
        except MachineCommunicationTimeout as e:
            logging.error('Node unreachable')

        self._machine_thread = Thread(target=self._machine_loop)
        self._machine_thread.daemon = True
        self._machine_thread.start()

    def wait_for_reply(self, future):
        if future.event.wait(future.timeout):
            return future.result
        raise MachineCommunicationTimeout('Timeout in %s' % str(future))

    def exit(self):
        del self.driver
        self.running_ev.set()

    def handle(self, message, **kwargs):
        try:
            self.messages_queue.put(message, block=False)
        except queue.Full as e:
            fe = FatalMachineError('Incoming queue is full', e)
            logging.error(str(fe))
            raise fe

    def find_matching_future(self, msg, delete=True):
        future = None
        findex = None

        if msg.uid: # Find by UUID
            for i, f in enumerate(self.waiting_futures):
                if msg == f:
                    future = f
                    findex = i
                    break
        else: # Find by path
            p = msg.path
            if p.endswith('/ok') or \
                    p.endswith('/error') or \
                    p.endswith('/reply'):
                p = '/'.join(p.split('/')[:-1])

            for i, f in enumerate(self.waiting_futures):
                if p == f.request.path:
                    future = f
                    findex = i
                    break

        del self.waiting_futures[findex]
        return future

    def update_local_status(self):
        self.request_machine_var('machine:error_code')

        if self.control_mode == ControlMode.Velocity:
            self.request_machine_var('machine:velocity')
            self.request_machine_var('machine:acceleration')
            self.request_machine_var('machine:deceleration')
        elif self.control_mode == ControlMode.Torque:
            pass
        elif self.control_mode == ControlMode.Position:
            pass

    def request_machine_var(self, var):
        f = self.send('/machine/get', var)
        f.set_callback(self.update_machine_var)

    def update_machine_var(self, f):
        self._local_status[f.request.args[0]] = f.result.args[1]

    def reply(self, command):
        if command.answer is not None:
            self.send_message(command.protocol, command.answer)

    def send(self, *args, **kwargs):
        re = kwargs.pop('reply_expected', True)
        m = self.message(*args, **kwargs)
        f = None
        if re:
            f = Future(m)
            self.waiting_futures.append(f)
        self.driver._send(m)

        return f

    #Properties

    @property
    def infos(self):
        rev = self.cape_infos['revision'] if self.cape_infos \
            else '0000'
        var = self.config['machine']['variant'].split('.')

        return ('identify', var[0].upper(), var[1].upper(), rev)

    @property
    def port(self):
        return self._port

    # Private methods

    def _machine_loop(self):
        """
        Handle machine logic
        """
        while not self.running_ev.is_set():
            try:
                if self.machine_class is None:
                    if self.machine_type is not MachineType.NONE:
                        # Load corresponding class
                        self.machine_class = get_machine_class(self.machine_type)
                    self.running_ev.wait(0.1)
                    continue

                self.update_local_status()

                self.running_ev.wait(self.refresh_interval)
            except MachineCommunicationTimeout as e:
                self.timeout_ev.set()
                logging.exception(e)
            except Exception as e:
                logging.exception(e)

    def _communication_loop(self):
        """
        Handle incoming messages from target
        """
        while not self.running_ev.is_set():
            try:
                try:
                    msg = self.messages_queue.get(block=True, timeout=1)
                except queue.Empty:
                    continue

                future = self.find_matching_future(msg)
                if future is None:
                    logging.info('No future for %s' % str(msg))
                    # A command might be sent from the remote node (error,
                    # event, etc)
                    # TODO: Here should be a function to handle this case
                    self.messages_queue.task_done()
                    continue

                future.set_result(msg)
                self.messages_queue.task_done()
            except Exception as e:
                logging.exception(e)



    def __getitem__(self, key):
        dst = self._get_destination(key)
        key = key.split(':', maxsplit=1)[1]

        if dst is not self:
            return dst[key]

        if self.slave_mode:
            self._last_command_time = time.time()

        return self.machine_keys[key]

    def __setitem__(self, key, value):
        if isinstance(value, (tuple, list)) and len(value) == 1:
            value, = value

        dst = self._get_destination(key)
        key = key.split(':', maxsplit=1)[1]

        if dst is not self:
            dst[key] = value
            return dst[key]

        if self.slave_mode:
            if self._timeout_event.is_set() and not self['machine:status:drive_enable']:
                self.machine_keys['machine:command:enable'] = True
                self._timeout_event.clear()
            self._last_command_time = time.time()
        elif self.master_mode:
            if 'command:enable' in key:
                for sm in self.slave_machines.values():
                    sm.set_to_remote('machine:command:enable', True if value else False)

        self.machine_keys[key] = value

    def getitem(self, key):
        return getattr(self, key)

    def setitem(self, key, value):
        setattr(self, key, value)

    def message(self, *args, **kwargs):
        return OscMessage(*args, receiver=self._target, **kwargs)


class Future(object):
    """
    Holds a sent message waiting for a reply.
    """

    def __init__(self, msg, uid=None):
        self._callback = None
        self._exception = None
        self._result = None
        self._event = Event()
        self._uid = uid or msg.path
        self._request = msg

        self.timeout = 1.0

    def set_callback(self, cb):
        if self._callback:
            raise ValueError('Callback is already defined')
        self._callback = cb

    @property
    def event(self):
        if not self._event:
            raise ValueError('Event is not defined')
        return self._event

    @property
    def request(self):
        return self._request

    def set_result(self, result):
        if self._result is not None:
            raise ValueError('Result is already defined')
        self._result = result
        self.event.set()
        if isinstance(self.result, Exception):
            raise self.result
        if isinstance(self.result, (list, tuple)):
            self._exception = self.result[1]

        if self._callback:
            self._callback(self)

    @property
    def result(self):
        if self._exception:
            raise self._exception
        if not self._result:
            raise ValueError('Result is not yet defined')
        return self._result

    def __eq__(self, other):
        try:
            if not (hasattr(other, 'uid') or hasattr(other, 'path')):
                raise AttributeError('No uid and path attributes')

            if hasattr(other, 'uid') and self.uid == other.uid:
                return True
            if self.uid == other.path:
                return True
            return False
        except AttributeError as e:
            raise TypeError('%s is not comparable with %s: %s' % (
                self.__class__.__name__, other.__class__.__name__, str(e)))

    @property
    def uid(self):
        return self._uid

    def __repr__(self):
        return 'WF {}'.format(self.uid)
