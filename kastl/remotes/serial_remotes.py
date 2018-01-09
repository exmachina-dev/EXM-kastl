#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""
Serial remotes
"""

from .exceptions import RemoteError, RemoteTimeoutError
from ..motion.exceptions import MotionError
from .abstract_remote import AbstractRemote
from ..processors.serial import SerialMessage
from ..motion.request import MotionRequest

import logging


logging = logging.getLogger('kastl.remotes.serial')


class SerialRemote(AbstractRemote):
    PROTOCOL = 'Serial'
    HAS_IP = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.local_status = dict()

        # Order is miportant here because the handle will stop filtering in an
        # exclusive filter accepts the message
        self.register_filter(protocol=self.PROTOCOL, target=self.timeout_reset)
        self.register_filter(protocol=self.PROTOCOL, target=self.handle_get,
                             alias_mask='machine.get', args_length=1,
                             exclusive=True)
        self.register_filter(protocol=self.PROTOCOL, target=self.handle_set,
                             alias_mask='machine.set',
                             exclusive=True)

    def main_loop(self, *args, **kwargs):
        while not self.running_ev.is_set():
            self.running_ev.wait(self.INTERVAL)

    def handle_get(self, m):
        k = m.args[0].decode()

        try:
            v = self.local_status[k]
            if callable(v):
                v = v()
            self.reply_ok(m, k, v)
        except KeyError:
            self.reply_error(m, k, 'No value for key.')

    def handle_set(self, m):
        try:
            k, a, = m.args
            nk = k.decode()
            if nk.startswith('machine.'):
                nk = nk[7:] # Strip machine. from key

            if nk in MotionRequest.TYPES:
                mr = MotionRequest(nk, *a)
                self.command_queue.put(mr)
                mr.done_ev.wait(self.request_timeout)
                if mr.done:
                    self.reply_ok(m, k, *a)
                else:
                    e = MotionError('Timeout while setting %s to %s' %
                                            str(k), ', '.join([str(sa) for si in a]))
                    self.reply_error(m, k, e)
                    raise e
            else:
                print(k, a)
        except Exception as e:
            logging.exception(e)

    def timeout_reset(self, m):
        self._last_message_time = time.time()

    def reply_ok(self, msg, *args, **kwargs):
        self.reply(msg, *args, add_path='ok', **kwargs)

    def reply_error(self, msg, *args, **kwargs):
        self.reply(msg, *args, add_path='error', **kwargs)

    def reply(self, msg, *args, **kwargs):
        ap = kwargs.pop('add_path', None)
        if ap:
            if not isinstance(ap, str):
                raise TypeError('add_path kwarg must be a string')

            full_path = msg.command + ap \
                if ap.startswith(msg.SEP) \
                else '{0.command}{0.SEP}{1}'.format(msg, ap)
        else:
            full_path = self.command

        self.send(full_path, *args, **kwargs)

    def send(self, *args, **kwargs):
        msg = kwargs['msg'] if 'msg' in kwargs else \
            self.message()

        for d in args:
            msg.cmd_bytes += d

        return self.send_message(msg)

    def message(self, *args, **kwargs):
        return SerialMessage(*args, **kwargs)

    @property
    def uid(self):
        return self.__class__.__name__


class SerialVarmoRemote(SerialRemote):
    HAS_FEEDBACK = False
    REFRESH_INTERVAL = 1.0
