# -*- coding: utf-8 -*-

from threading import Thread
from threading import Event
from queue import Queue, Empty
from collections import namedtuple
from datetime import datetime
import logging
import functools

from .abstract_machine import AbstractMachine
from .abstract_machine import AbstractMachineError, AbstractFatalMachineError

from ..drivers import get_driver
from ..drivers.abstract_driver import AbstractDriverError, AbstractTimeoutError

logging = logging.getLogger('kastl.machine.slave')

Slave = namedtuple('Slave', ('serialnumber', 'address', 'driver', 'slave_mode', 'config'))
SlaveKey = namedtuple('SlaveKey', ('dest', 'source'))


CONTROL_MODES = {
    'torque':           1,
    'velocity':         2,
    'position':         3,
    'enhanced_torque':  4,
}


class SlaveMachineError(AbstractMachineError):
    pass


class FatalSlaveMachineError(AbstractFatalMachineError):
    fatal_event = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if FatalSlaveMachineError:
            FatalSlaveMachineError.fatal_event.set()
            logging.error('Fatal error, disabling all slaves')


class SlaveRequest(object):
    def __init__(self, attr, *args, **kwargs):
        self._args = ()
        self._attr = None
        if 'getitem' in kwargs and kwargs['getitem']:
            self._item = attr
        elif 'setitem' in kwargs and kwargs['setitem']:
            self._item = attr
            self._args = args
        else:
            self._attr = attr
            self._args = args

        self._kwargs = {
            'getitem': False,
            'setitem': False,
        }
        self._kwargs.update(kwargs)
        self._callback = None

    def set_callback(self, cb):
        self._callback = cb

    @property
    def attribute(self):
        return self._attr

    @property
    def item(self):
        return self._item

    @property
    def args(self):
        return self._args

    @property
    def kwargs(self):
        return self._kwargs

    @property
    def callback(self):
        return self._callback

    def __getattr__(self, name):
        return self._kwargs[name]

    def __repr__(self):
        return '{} {} {} {}'.format('RQ', self.attribute,
                                    ' '.join(map(str, self.args)), self.callback)


class SlaveMachine(AbstractMachine):

    machine = None
    fatal_event = None

    SLAVE_MODES = {
        'torque': (
            SlaveKey('machine:torque_ref', 'machine:torque'),
            SlaveKey('machine:torque_rise_time', 'machine:torque_rise_time'),
            SlaveKey('machine:torque_fall_time', 'machine:torque_fall_time'),
        ),
        'enhanced_torque': (
            SlaveKey('machine:torque_ref', 'machine:current'),
            SlaveKey('machine:velocity_ref', 'machine:velocity'),
            SlaveKey('machine:torque_rise_time', None),
            SlaveKey('machine:torque_fall_time', None),
        ),
        'velocity': (
            SlaveKey('machine:velocity_ref', 'machine:velocity'),
            SlaveKey('machine:acceleration', None),
            SlaveKey('machine:deceleration', None),
        ),
    }

    def __init__(self, **kwargs):
        for k in ('address', 'driver_type', 'motion_mode', 'config'):
            if k not in kwargs:
                raise ValueError('Missing required argument: %s' % k)

        self.config = kwargs['config']
        self.driver_type = kwargs['driver_type']

        addr = kwargs['address'].split(':')[0:2]
        port = 6969
        if len(addr) == 2:
            addr, port = addr
        else:
            addr, = addr

        self.driver_config = {
            'target_address': addr,
            'target_port': int(port),
            'timeout': float(self.config.get('timeout', .5)),
        }

        self.timeout = self.driver_config['timeout']
        self.refresh_interval = float(self.config.get('refresh_interval', 0.5))

        self.bridge = Queue()

        self._get_dict = {}
        self._set_dict = {}
        self._latency = None

        self.last_values = {}

        self.errors = 0
        self.max_errors = 10

        self.watchdog_ev = Event()

        self._thread = None
        self._watchdog_thread = None

    def init_driver(self):
        drv = self.driver_type
        if not drv:
            e = ValueError('Driver not defined for machine with S/N %s' % (self.serialnumber))
            logging.error('{!s}'.format(e))
            raise e

        logging.info("Loading %s driver" % drv)

        try:
            driver = Driver().get_driver(drv)
            self.driver = driver(self.driver_config)
            self.inlet = self.driver.init_queue()
        except KeyError:
            logging.error("Unable to get %s driver, aborting." % drv)
            return
        except AbstractDriverError as e:
            raise SlaveMachineError('Unable to intialize driver: %s' % e)

        logging.debug("%s driver loaded" % drv)
        return drv

    def start(self, **kwargs):
        if self._thread:
            self.running_event.set()
            self._thread.join()

        self.running_event.clear()
        self.driver.connect()

        self._thread = Thread(target=self.loop)
        self._thread.daemon = True
        self._thread.start()

        if kwargs.get('watchdog', True):
            self.start_watchdog()

    def start_watchdog(self):
        if self._watchdog_thread:
            self.watchdog_event.set()
            self._watchdog_thread.join()

        self.watchdog_event.clear()
        self._watchdog_thread = Thread(target=self._watchdog)
        self._watchdog_thread.daemon = True
        self._watchdog_thread.start()

    def exit(self):
        self.running_event.set()
        self.driver.exit()

    def loop(self):
        while True:
            try:
                self.set_control_mode(self.slave.slave_mode)
                self.set('machine:command:enable', False)
                break
            except SlaveMachineError as e:
                logging.error('Exception in {n} loop: {e}'.format(
                    n=self.__class__.__name__, e=e))
            except AbstractTimeoutError as e:
                logging.error('Timeout for {!s}'.format(self))
            except Exception as e:
                logging.error('Uncatched exception in {n} loop: {e}'.format(
                    n=self.__class__.__name__, e=e))

        while not self.running_event.is_set():
            try:
                recv_item = self.bridge.get(block=True, timeout=2)
                if not isinstance(recv_item, SlaveRequest):
                    logging.error('Unsupported object in queue: %s' % repr(recv_item))
                    continue

                try:
                    if recv_item.getitem:
                        res = self.driver[recv_item.item]
                    elif recv_item.setitem:
                        res = self.driver.__setitem__(recv_item.item, *recv_item.args)
                    else:
                        res = getattr(self.driver, recv_item.attribute)(
                            *recv_item.args)

                    recv_item.callback(res)
                except AttributeError:
                    logging.exception('''Can't find %s in driver''' % recv_item.attribute)
                except SlaveMachineError as e:
                    logging.error('Exception in {n} loop: {e}'.format(
                        n=self.__class__.__name__, e=e))
                except AbstractTimeoutError as e:
                    logging.error('Timeout for {!s}'.format(self))
                except Exception as e:
                    logging.error('Uncatched exception in {n} loop: {e}'.format(
                        n=self.__class__.__name__, e=e))
                self.bridge.task_done()
            except Empty:
                pass

    def watcher_loop(self):
        smode = self.slave.slave_mode
        self.last_values = {}
        self.set_control_mode(smode)
        while not self.running_event.is_set():
            if SlaveMachine.fatal_event.is_set():
                self.set_to_remote('machine:command:enable', False)
                self.running_event.wait(self.refresh_interval)
                continue

            try:
                try:
                    for skey in self.SLAVE_MODES[smode]:
                        self._send_if_latest(skey.dest, source=skey.source)
                    self.errors = 0
                except KeyError:
                    raise FatalSlaveMachineError(
                        'Unrecognized mode for slave {!s}: {}'.format(self, smode))
            except AbstractFatalMachineError as e:
                if self.errors > self.max_errors:
                    self.set_to_remote('machine:command:enable', False)
                    if SlaveMachine.fatal_event:
                        SlaveMachine.fatal_event.set()
                    logging.error('Slave machine disabled')
                    continue
                else:
                    self.errors += 1
                logging.error('Fatal exception occured in slave watcher loop '
                              'for {!s}: {!r}'.format(self, e))
            except AbstractMachineError as e:
                logging.error('Exception occured in slave watcher loop '
                              'for {!s}: {!r}'.format(self, e))
            except Exception as e:
                logging.error('Exception in {0} loop: {1}'.format(self.__class__.__name__, e))

            self.running_event.wait(self.refresh_interval)

    def request_from_remote(self, callback, attribute, *args, **kwargs):
        event = kwargs.pop('event', None)
        rq = SlaveRequest(attribute, *args, **kwargs)
        if event:
            callback = functools.partial(callback, event=event)

        rq.set_callback(callback)

        self.bridge.put(rq)
        return rq

    def send(self, rq, *args, **kwargs):
        if SlaveKey(rq.item, rq.source) not in self.forward_keys:
            return

        event = kwargs.pop('event', None)
        callback = kwargs.pop('callback', None)
        if event:
            callback = functools.partial(callback, event=event)

        value = rq.args[0]
        rq = self._send_if_latest(rq.item, rq.source, value=value)

        if rq is not None:
            rq.set_callback(callback)

        return rq

    def enslave(self):
        self.set_to_remote('machine:operating_mode', 'slave', self.machine.get_address(self.slave.driver))

    @property
    def forward_keys(self):
        return self.SLAVE_MODES[self.slave.slave_mode]

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
        return self.get_from_remote('machine:serialnumber', block=True)

    def ping(self, block=True):
        ev = Event() if block is True else None

        start_time = datetime.now()
        cb = functools.partial(self._ping_cb, start_time)
        rq = self.request_from_remote(cb, 'ping', event=ev)

        if ev is not None and ev.wait(self.timeout):
            return self._latency
        return rq

    def get_from_remote(self, key, **kwargs):
        ev = Event() if 'block' in kwargs and kwargs['block'] is True else None

        rq = self.request_from_remote(self._get_cb, key, getitem=True, event=ev)

        if ev is not None and ev.wait(self.timeout):
            return self._get_dict[key]
        return rq

    def set_to_remote(self, key, *args, **kwargs):
        ev = Event() if 'block' in kwargs and kwargs['block'] is True else None

        rq = self.request_from_remote(self._set_cb, key, *args, setitem=True, event=ev)

        if ev is not None and ev.wait(self.timeout):
            return self._set_dict[key]
        return rq

    def set_control_mode(self, mode):
        if mode not in CONTROL_MODES.keys():
            raise KeyError('Unexpected mode: {0}'.format(mode))

        return self.set_to_remote('machine:command:control_mode', CONTROL_MODES[mode], block=True)

    def get(self, key, **kwargs):
        return self.driver.get(key, **kwargs)

    def set(self, key, *args, **kwargs):
        return self.driver.set(key, *args, **kwargs)

    def _send_if_latest(self, dest, source=None, **kwargs):
        source = source if source is not None else dest
        lvalue = self.last_values.get(dest, None)

        value = kwargs.get('value', None)

        try:
            value = self.machine.machine_keys.get_value_for_slave(self, source, value)
        except SlaveMachineError as e:
            logging.warn('Exception in {0!s}: {1!s}'.format(self, e))
        except AbstractMachineError:
            logging.warn('Machine is not ready')
        except Exception as e:
            logging.exception('Exception in {0!s}: {1!s}'.format(self, e))
            raise SlaveMachineError('{!s}'.format(e))

        if value is None:
            raise SlaveMachineError('{0} returned None for {1!s}'.format(source, self))

        rq = None
        if lvalue:
            if value != lvalue:
                rq = self.set_to_remote(dest, value)
                self.last_values[dest] = value
        else:
            rq = self.set_to_remote(dest, value)
            self.last_values[dest] = value

        return rq

    def _watchdog(self):
        while not self.watchdog_event.is_set():
            if self.fatal_event.is_set() or self.fault_event.is_set():
                self.set('machine:command:enable', False)

            self.watchdog_event.wait(self.refresh_interval)

    def _ping_cb(self, start_time, data, event=None):
        rtn = self._default_cb(data, event)

        if rtn:
            dt = datetime.now() - start_time
            self._latency = dt.microseconds / 1000

        if event:
            event.set()

    def _get_cb(self, data, event=None):
        try:
            rtn = self._default_cb(data, event)
            logging.debug('Rtn data: %s' % rtn)
        except SlaveMachineError as e:
            logging.error(repr(e))
            return

        if rtn:
            self._get_dict[rtn.args[1]] = rtn.args[2]
        else:
            raise SlaveMachineError('No data in {}'.format(rtn))

        if event:
            event.set()

    def _set_cb(self, data, event=None):
        try:
            rtn = self._default_cb(data, event)
            logging.debug('Rtn data: %s' % rtn)
        except SlaveMachineError as e:
            logging.error(repr(e))
            return

        if rtn:
            self._set_dict[rtn.args[1]] = rtn.args[2]
        else:
            raise SlaveMachineError('No data in {}'.format(rtn))

        if event:
            event.set()

    def _default_cb(self, data, event=None):
        exc = None
        if isinstance(data, (list, tuple)) and len(data) == 2:
            data, exc = data

        if event and exc and isinstance(exc, Exception):
            event.set()
            raise exc

        if not data:
            if event:
                event.set()
            raise SlaveMachineError('No data')

        if '/ok' in data.path:
            return data
        elif '/error' in data.path:
            e = {
                'path': data.path,
                'args': ' '.join(data.args),
            }
            raise SlaveMachineError('Got error in {path}: {args}'.format(**e))

    def __repr__(self):
        i = {
            'name': self.__class__.__name__,
            'addr': self.slave.address,
            'port': self.driver_config['target_port'],
            'prot': self.slave.driver,
            'serial': self.slave.serialnumber,
            'mode': self.slave.slave_mode,
        }
        return '{name}: {addr}:{port} via {prot} ({serial}) in {mode} mode'.format(**i)

    def __str__(self):
        i = {
            'addr': self.slave.address,
            'port': self.driver_config['target_port'],
            'prot': self.slave.driver.lower(),
            'serial': self.slave.serialnumber,
        }
        return '{addr}:{port} via {prot} ({serial})'.format(**i)
