# -*- coding: utf-8 -*-

import liblo as lo
import logging
from threading import Thread
from threading import Event
from queue import Queue
import uuid

from .abstract_driver import AbstractDriver, AbstractDriverError, AbstractTimeoutError
from ..processors.osc import OscAddress, OscMessage

logging = logging.getLogger('kastl.driver.osc')


class OscDriverError(AbstractDriverError):
    pass


class OscDriverTimeout(OscDriverError, AbstractTimeoutError):
    pass


class OscDriver(AbstractDriver):
    def __init__(self, config):
        self.target_address = config.get("target_address")
        self.target_port = int(config.get("target_port", 6969))
        self.target = OscAddress(hostname=self.target_address,
                                 port=self.target_port)

        self.running = Event()
        self.timeout = config.get('timeout', 0.25)

        self._waiting_futures = []

        self.queue = Queue(maxsize=45)

    def connect(self):
        self._thread = Thread(target=self.from_machine)
        self._thread.daemon = True
        self._thread.start()

    def register(self):
        try:
            sn = self.MOTIONSERVER.serialnumber or False
            if sn:
                m = self.message('/slave/register', sn, types='s')
            else:
                m = self.message('/slave/register', sn, types='F')

            self.to_machine(m)
        except AbstractDriverError as e:
            logging.exception('Error while registering: %s' % str(e))

    def exit(self):
        self['machine:command:stop'] = True
        self['machine:command:enable'] = False


        self.running.set()

    def send(path, *arg, **kwargs):

        if kwargs.get('reply_expected', True):
            f = Future(msg)
            self.waiting_futures.append(f)

    def message(self, *args, **kwargs):
        return OscMessage(*args, receiver=self.target, **kwargs)

    def ping(self):
        m = self.message('/slave/ping')
        fut = self.to_machine(m)
        reply = None
        try:
            reply = self.wait_for_future(fut)
            return reply
        except OscDriverTimeout as e:
            logging.error(e)
            return reply, e

    def to_machine(self, request, uid=None):
        try:
            if not uid:
                uid = uuid.uuid4().hex
            event = Event()
            future = OscFutureResult(uid)
            future.set_callback(self.done_cb)
            future.set_event(event)
            self._waiting_futures.append(future)
            self._send(request, uid)
            return future
        except:
            raise

    def from_machine(self):
        while not self.running.is_set():
            try:
                recv_item = self.queue.get(block=True)

                future = None
                for i, f in enumerate(self._waiting_futures):
                    if recv_item == f:
                        future = f
                        f_id = i
                        break

                if not future:
                    logging.error('Unable to find waiting future '
                                  'for %s' % str(f))
                    continue

                del self._waiting_futures[f_id]

                if self._check_error(recv_item):
                    future.set_result((recv_item, OscDriverError(str(recv_item))))
                else:
                    future.set_result(recv_item)

                self.queue.task_done()
            except OscDriverTimeout as e:
                logging.error('Timeout in %s: %s' % (self.__class__.__name__,
                                                     repr(e)))
            except OscDriverError as e:
                logging.error('Exception in %s: %s' % (self.__class__.__name__,
                                                       repr(e)))

    def done_cb(self, *args):
        pass

    def wait_for_future(self, fut):
        if fut.event.wait(self.timeout):
            return fut.result
        raise OscDriverTimeout('Timeout while waiting for %s' % repr(fut))

    def get(self, key, **kwargs):
        m = self.message('/slave/get', key)
        fut = self.to_machine(m)
        try:
            if kwargs.get('block', True):
                ret = self.wait_for_future(fut)
                return ret
            else:
                return fut
        except OscDriverTimeout as e:
            logging.error(e)
            raise e
        except OscDriverError as e:
            logging.error(e)

    def set(self, key, *args, **kwargs):
        m = self.message('/slave/set', key, *args)
        fut = self.to_machine(m)
        try:
            if kwargs.get('block', True):
                ret = self.wait_for_future(fut)
                return ret
            else:
                return fut
        except OscDriverTimeout as e:
            logging.error(e)
            raise e
        except OscDriverError as e:
            logging.error(e)

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, *args):
        return self.set(key, *args)

    def _send(self, message, *args, **kwargs):
        try:
            m = self.message(message.path, *message.args)
            m.receiver = self.target
            lo.send((m.receiver.hostname, m.receiver.port), m.message)
        except OSError as e:
            raise OscDriverError(str(e))

    def _check_error(self, command):
        if command.path.endswith('/error'):
            return True


class OscFutureResult(object):
    def __init__(self, uid):
        self._callback = None
        self._exception = None
        self._result = None
        self._event = None
        self._uid = uid

    def set_callback(self, cb):
        if self._callback:
            raise ValueError('Callback is already defined')
        self._callback = cb

    def set_event(self, event):
        if self._event:
            raise ValueError('Event is already defined')
        self._event = event

    @property
    def event(self):
        if not self._event:
            raise ValueError('Event is not defined')
        return self._event

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
            if self.uid == other.uid:
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
