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

logging = logging.getLogger('kastl.machine')


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

        try:
            self.control_mode = self.config.get('control_mode', fallback='velocity')
            self.control_mode = ControlMode[self.control_mode.title()]
        except KeyError as e:
            logging.error('No such control mode: %s', e)

        self.waiting_futures = list()
        self.driver = None
        self.refresh_interval = 0.25

        self._comms_thread = None
        self._machine_thread = None

        self._local_status = dict()
        self._local_requests = dict()

        self.last_command_time = time.time()

        self.init_communication()

    def init_communication(self):
        "Loads the appropriate driver"

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
        "Starts the underlying mechanism."

        if self.connect():
            self.send_configuration()

    def connect(self):
        """
        Starts communication thread and request basic informations like version
        and variant.
        """

        self._comms_thread = Thread(target=self._communication_loop)
        self._comms_thread.daemon = True
        self._comms_thread.start()

        try:

            def cb(msg):
                if len(msg.result.args):
                    self.version = msg.result.args[0]

            f = self.send('/version')
            f.set_callback(cb)

            def cb(msg):
                if len(msg.result.args):
                    self.variant = str(msg.result.args[1])
                    self.machine_type = get_machine_type(self.variant)
                    logging.info('%s is a %s.', self.serialnumber, self.machine_type.name)

            f = self.send('/config/get', 'machine:variant')
            f.set_callback(cb)


            print(f)
        except MachineCommunicationTimeout as e:
            logging.error('Node unreachable')

        self._machine_thread = Thread(target=self._machine_loop)
        self._machine_thread.daemon = True
        self._machine_thread.start()

    def wait_for_reply(self, future):
        """
        Wait for a reply in future and raise a MachineCommunicationTimeout
        if the machine takes too long to respond.
        """

        if future.event.wait(future.timeout):
            return future.result
        raise MachineCommunicationTimeout('Timeout in %s' % str(future))

    def exit(self):
        "Close the communication and delete the driver"

        self.running_ev.set()
        self._machine_thread.join()
        self._comms_thread.join()
        del self.driver

    def handle(self, message, **kwargs):
        "Handle an incoming message."
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

    def send_local_requests(self):
        for k in self._local_requests.keys():
            v = self._local_status.pop(k)
            self.send_machine_var(k, v)

    def update_local_status(self):
        self.request_machine_var('machine:error_code')
        self.request_machine_var('machine:status')

        if self.control_mode == ControlMode.Velocity:
            self.request_machine_var('machine:velocity')
            self.request_machine_var('machine:acceleration')
            self.request_machine_var('machine:deceleration')
        elif self.control_mode == ControlMode.Torque:
            self.request_machine_var('machine:velocity')
            self.request_machine_var('machine:torque_rise_time')
            self.request_machine_var('machine:torque_fall_time')
        elif self.control_mode == ControlMode.Position:
            self.request_machine_var('machine:velocity')
            self.request_machine_var('machine:position')
            self.request_machine_var('machine:acceleration')
            self.request_machine_var('machine:deceleration')

    def request_machine_var(self, var):
        f = self.send('/machine/get', var)
        f.set_callback(self.update_machine_var)

    def send_machine_var(self, var):
        f = self.send('/machine/set', var)
        # FIXME: Should we can a separate dict for those ?
        f.set_callback(self.update_machine_var)

    def update_machine_var(self, f):
        if not f.result.is_error:
            if f.request.args[0] != f.result.args[0]:
                print(f.request.args[0], f.result.args[0])
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

    def message(self, *args, **kwargs):
        return OscMessage(*args, receiver=self._target, **kwargs)

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
                self.send_local_requests()

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
                    logging.debug('No future for %s' % str(msg))
                    # A command might be sent from the remote node (error,
                    # event, etc)
                    # TODO: Here should be a function to handle this case
                    self.messages_queue.task_done()
                    continue

                future.set_result(msg)
                self.messages_queue.task_done()
            except Exception as e:
                logging.exception(e)

    # Special methods

    def __getitem__(self, key):
        return self._local_status[key]

    def __setitem__(self, key, value):
        self._local_requests[key] = value

    def getitem(self, key):
        return getattr(self, key)

    def setitem(self, key, value):
        setattr(self, key, value)

    def __str__(self):
        return '%s %s at %s' % (self.__class__.__name__, self.serialnumber,
                                self.ip_address)


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
    def event(self):
        if not self._event:
            raise ValueError('Event is not defined')
        return self._event

    @property
    def request(self):
        return self._request

    @property
    def result(self):
        if self._exception:
            raise self._exception
        if not self._result:
            raise ValueError('Result is not yet defined')
        return self._result

    @property
    def uid(self):
        return self._uid

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

    def __repr__(self):
        return 'WF {}'.format(self.uid)
